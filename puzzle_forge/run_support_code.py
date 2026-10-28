import os
import requests
import re
import yaml
import subprocess
import time
import json
import sys
import asyncio
import argparse
import tempfile
Path = "/mnt/omniSSD/user_workspace/xiongkai/llm_general_r1/llm-eval/tools/"
sys.path.append(Path)
from ExternalApi import DEEPSEEKClient 

# 提取YAML内容和Python代码
def extract_yaml_and_code(text):
    """从模型输出中提取YAML内容和Python代码"""
    # 提取YAML内容
    yaml_pattern = r'#### final yaml begin\s*(.*?)\s*#### final yaml end'
    yaml_matches = re.findall(yaml_pattern, text, re.DOTALL)
    yaml_content = None
    
    if yaml_matches:
        yaml_content = yaml_matches[-1].strip()
        # 如果YAML内容中包含```yaml代码块，提取其中的内容
        yaml_code_pattern = r'```yaml\s*(.*?)\s*```'
        yaml_code_matches = re.findall(yaml_code_pattern, yaml_content, re.DOTALL)
        if yaml_code_matches:
            yaml_content = yaml_code_matches[-1].strip()
        else:
            # 如果没有```yaml标记，直接使用提取的内容
            yaml_content = yaml_content.strip()
    
    # 提取Python代码
    code_pattern = r'#### final code begin\s*(.*?)\s*#### final code end'
    code_matches = re.findall(code_pattern, text, re.DOTALL)
    python_code = None
    
    if code_matches:
        python_code = code_matches[-1].strip()
        # 如果Python代码中包含```python代码块，提取其中的内容
        python_code_pattern = r'```python\s*(.*?)\s*```'
        python_code_matches = re.findall(python_code_pattern, python_code, re.DOTALL)
        if python_code_matches:
            python_code = python_code_matches[-1].strip()
        else:
            # 如果都没有标记，直接使用提取的内容
            python_code = python_code.strip()
    
    return yaml_content, python_code

def extract_yaml_content(text):
    """从模型输出中提取YAML内容（向后兼容）"""
    # 首先尝试新格式
    yaml_content, _ = extract_yaml_and_code(text)
    if yaml_content:
        return yaml_content
    
    # 如果没有找到新格式，尝试旧格式
    pattern = r'```yaml\s*(.*?)\s*```'
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[-1] if matches else None

def extract_question_content(text, question_num):
    """提取指定问题的内容"""
    pattern = rf'# question {question_num} begin\s*(.*?)\s*# question {question_num} end'
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[-1].strip() if matches else None

def extract_error_info(error_output):
    """提取完整的错误信息，直到最后一行During handling之前"""
    if not error_output:
        return "未知错误"
    
    error_lines = error_output.strip().split('\n')
    error_info_lines = []
    
    # 查找所有"During handling of the above exception"的位置
    during_handling_indices = []
    for i, line in enumerate(error_lines):
        if "During handling of the above exception, another exception occurred:" in line:
            during_handling_indices.append(i)
    
    if during_handling_indices:
        # 取最后一个"During handling"的位置
        last_during_handling_index = during_handling_indices[-1]
        # 提取最后一个"During handling"之前的所有行
        error_info_lines = error_lines[:last_during_handling_index]
    else:
        # 如果没有找到"During handling"，则返回所有错误信息
        error_info_lines = error_lines
    
    return '\n'.join(error_info_lines).strip()

def run_output_py_and_get_error():
    """运行output.py文件并获取其输出作为错误信息"""
    output_py_path = '/mnt/omniSSD/user_workspace/xiongkai/smt-master/output.py'
    
    if not os.path.exists(output_py_path):
        return None
    
    try:
        # 运行output.py文件
        result = subprocess.run(
            ['python', output_py_path],
            capture_output=True, 
            text=True, 
            timeout=30,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        
        # 组合所有输出
        full_output = ""
        if result.stdout:
            full_output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            full_output += f"STDERR:\n{result.stderr}\n"
        
        # 删除output.py文件
        try:
            os.remove(output_py_path)
            print("已删除output.py文件")
        except Exception as e:
            print(f"删除output.py文件失败: {str(e)}")
        
        return full_output.strip() if full_output.strip() else "output.py运行无输出"
        
    except subprocess.TimeoutExpired:
        # 仍然尝试删除文件
        try:
            os.remove(output_py_path)
        except:
            pass
        return "output.py执行超时"
    except Exception as e:
        # 仍然尝试删除文件
        try:
            os.remove(output_py_path)
        except:
            pass
        return f"output.py执行异常: {str(e)}"

def save_yaml_and_code(yaml_content, python_code, attempt_count, output_folder, each_question_name):
    """保存YAML内容和Python代码，并运行translator.py测试"""
    yaml_filename = os.path.join(output_folder, f"temp_output_{attempt_count}.yaml")
    python_filename = os.path.join(output_folder, f"temp_code_{attempt_count}.py")
    
    # 首先验证YAML语法
    try:
        parsed_yaml = yaml.safe_load(yaml_content)
        print("YAML语法验证通过")
    except yaml.YAMLError as e:
        error_msg = f"YAML语法错误: {str(e)}"
        print(error_msg)
        return False, error_msg, None
    
    # 保存YAML文件
    with open(yaml_filename, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    
    # 保存Python代码（如果存在）
    if python_code:
        with open(python_filename, 'w', encoding='utf-8') as f:
            f.write(python_code)
        with open(os.path.join("/mnt/omniSSD/user_workspace/xiongkai/smt-master", f"{each_question_name}.py"), 'w', encoding='utf-8') as f:
            f.write(python_code)
        print(f"Python代码已保存到: {python_filename}")
    
    try:
        # 运行translator.py，确保捕获所有输出
        result = subprocess.run(
            ['python', '/mnt/omniSSD/user_workspace/xiongkai/smt-master/translator.py', '-t', yaml_filename],
            capture_output=True, 
            text=True, 
            timeout=30,
            # 添加环境变量确保输出编码正确
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        
        # 检查是否生成了output.py文件
        output_py_path = '/mnt/omniSSD/user_workspace/xiongkai/smt-master/output.py'
        if os.path.exists(output_py_path):
            print("检测到生成了output.py文件，正在运行并获取输出...")
            output_py_result = run_output_py_and_get_error()
            
            # 仅使用output.py的输出作为错误信息
            full_output = output_py_result
            
            # 检查是否成功运行（返回码为0且输出中包含"answer:"）
            success_condition = (
                result.returncode == 0 and 
                "answer:" in result.stdout.lower()
            )
            
            if success_condition:
                print("运行成功！")
                return True, None, full_output
            else:
                # 如果返回码为0但没有"answer:"，说明有验证错误
                if result.returncode == 0 and "answer:" not in result.stdout.lower():
                    error_info = f"验证错误（无answer）:\n{full_output}"
                else:
                    error_info = full_output.strip() if full_output.strip() else f"返回码: {result.returncode}, 无错误信息"
                
                # 使用新的错误提取函数
                formatted_error = extract_error_info(error_info)
                return False, formatted_error or error_info, None
        else:
            # 原逻辑：没有生成output.py文件，仅使用translator.py的输出
            full_output = ""
            if result.stdout:
                full_output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                full_output += f"STDERR:\n{result.stderr}\n"
            
            # 检查是否成功运行（返回码为0且输出中包含"answer:"）
            success_condition = (
                result.returncode == 0 and 
                "answer:" in result.stdout.lower()
            )
            
            if success_condition:
                print("运行成功！")
                return True, None, result.stdout
            else:
                # 如果返回码为0但没有"answer:"，说明有验证错误
                if result.returncode == 0 and "answer:" not in result.stdout.lower():
                    error_info = f"验证错误（无answer）:\n{result.stdout}"
                else:
                    # 优先使用stderr，如果没有则使用stdout
                    error_info = result.stderr.strip() if result.stderr.strip() else result.stdout.strip()
                    if not error_info:
                        error_info = f"返回码: {result.returncode}, 无错误信息"
                
                # 使用新的错误提取函数
                formatted_error = extract_error_info(error_info)
                return False, formatted_error or error_info, None
            
    except subprocess.TimeoutExpired:
        # 检查是否生成了output.py并清理
        output_py_path = '/mnt/omniSSD/user_workspace/xiongkai/smt-master/output.py'
        if os.path.exists(output_py_path):
            try:
                os.remove(output_py_path)
            except:
                pass
        return False, "执行超时", None
    except Exception as e:
        # 检查是否生成了output.py并清理
        output_py_path = '/mnt/omniSSD/user_workspace/xiongkai/smt-master/output.py'
        if os.path.exists(output_py_path):
            try:
                os.remove(output_py_path)
            except:
                pass
        return False, f"执行异常: {str(e)}", None

def save_full_output(content, filename, output_folder):
    """保存模型的完整输出"""
    full_output_file = os.path.join(output_folder, filename)
    with open(full_output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"完整输出已保存到: {full_output_file}")

def save_conversation_history(messages, filename, output_folder):
    """保存完整的对话历史"""
    conversation_file = os.path.join(output_folder, filename)
    with open(conversation_file, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    print(f"对话历史已保存到: {conversation_file}")

async def evaluate_problem_validity(translator_output, model_client, messages_list, output_folder, eval_attempt):
    """评估生成的数学问题及答案是否合理"""
    evaluation_prompt = f"""大模型生成了一个数学问题：{translator_output}，不需要评估答案的正确性，只评估生成的数学问题题面和答案是否清晰，无歧义，合理，有意义，只回答是或否。
        以下述格式回答：
        # anlysis begin
        合理性: <是/否>
        原因：<原因>
        # anlysis end
        """
    # 创建新的对话历史，避免修改原始数据
    #evaluation_conversation = messages_list.copy()
    #evaluation_conversation.append(evaluation_prompt)
    evaluation_conversation = [
            {"role": "user", "content": evaluation_prompt}
        ]
    try:
        # 获取评估结果
        evaluation_response = await model_client.text2text({"messages": evaluation_conversation})
        
        # 检查返回类型
        if isinstance(evaluation_response, dict) and 'content' in evaluation_response:
            evaluation_content = evaluation_response['content']
        else:
            # 如果返回的不是期望的格式，尝试直接使用
            evaluation_content = str(evaluation_response)
        
        # 保存评估输出
        save_full_output(evaluation_content, f"evaluation_attempt_{eval_attempt}_output.txt", output_folder)
        
        # 将评估回复添加到对话历史
        assistant_response = {
            "role": "assistant", 
            "content": evaluation_content
        }
        evaluation_conversation.append(assistant_response)
        
        # 保存当前对话历史
        save_conversation_history(evaluation_conversation, f"evaluation_attempt_{eval_attempt}_conversation.json", output_folder)
        
        # 解析评估结果
        is_valid = "合理性: 是" in evaluation_content
        reason = evaluation_content if not is_valid else None
        
        print(f"第{eval_attempt}次评估结果: {'合理' if is_valid else '不合理'}")
        #if not is_valid:
        #    print(f"不合理原因: {reason}")
        
        return is_valid, reason, assistant_response
        
    except Exception as e:
        print(f"评估请求失败: {str(e)}")
        # 如果评估失败，默认认为不合理
        return False, f"评估过程出错: {str(e)}", None

async def generate_questions(n, original_question, model_client, output_folder):
    """生成n个相关数学问题，原问题为question_0，其他问题从1到n标号"""
    print(f"\n=== 开始生成 {n} 个相关数学问题 ===")
    
    # 首先将原始问题添加到结果列表中作为question_0
    generated_questions = [original_question]
    print(f"✅ 已将原始问题添加为question_0")
    
    # 读取Polish阶段的文件
    polish_folder_path = '/mnt/omniSSD/user_workspace/xiongkai/smt-master/prompts/Stage_Polish/'
    
    # 初始化对话历史
    input_content_begin = {
        'messages': []
    }
    
    # 批量读取Polish阶段文件内容并构建对话历史
    for i in range(1, 3):  # stage_1.md 到 stage_5.md
        file_name = f"stage_{i}.md"
        file_path = os.path.join(polish_folder_path, file_name)
        
        if not os.path.exists(file_path):
            print(f"警告: 文件 {file_path} 不存在")
            continue
            
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
        
        # 替换占位符
        file_content = file_content.replace('<n>', str(n))
        file_content = file_content.replace('<question>', original_question)
        
        message = {
            "role": "user",
            "content": file_content
        }
        
        input_content_begin['messages'].append(message)
        
        # 发送请求获取模型回复
        try:
            stage_response = await model_client.text2text(input_content_begin)
            
            # 检查返回类型并正确处理
            if isinstance(stage_response, dict) and 'content' in stage_response:
                response_content = stage_response['content']
            else:
                response_content = str(stage_response)
            
            # 将模型回复添加到对话历史
            input_content_begin['messages'].append({
                "role": "assistant", 
                "content": response_content
            })
            
            print(f"Polish Stage {i} 处理完成")
            
        except Exception as e:
            print(f"Polish Stage {i} 处理失败: {str(e)}")
            return None, None
    
    # 从最后一个回复中提取所有生成的问题
    last_response = input_content_begin['messages'][-1]['content']
    
    # 生成n个相关问题（加上原始问题，总共n+1个问题）
    for i in range(1, n + 1):  # 从1到n，生成n个问题
        question_content = extract_question_content(last_response, i)
        if question_content:
            # 对每个问题内容进行变量替换和数值优化处理
            processed_question = await process_single_question(question_content, model_client, output_folder, i)
            if processed_question:
                generated_questions.append(processed_question)
                print(f"✅ 成功处理问题 {i} (question_{i})")
            else:
                print(f"⚠️ 警告: 问题 {i} 处理失败，使用原始内容")
                generated_questions.append(question_content)
        else:
            print(f"⚠️ 警告: 未找到问题 {i}，跳过")
    
    # 保存生成的问题到文件
    question_folder = os.path.join(output_folder, "generated_questions")
    os.makedirs(question_folder, exist_ok=True)
    
    # 保存问题，question_0 是原始问题，question_1 到 question_{n} 是生成的问题
    for i, question in enumerate(generated_questions):
        question_file = os.path.join(question_folder, f"question_{i}.txt")
        with open(question_file, 'w', encoding='utf-8') as f:
            f.write(question)
        print(f"问题 {i} 已保存到: {question_file}")
    
    # 保存完整的Polish对话历史
    save_conversation_history(input_content_begin['messages'], "polish_conversation.json", output_folder)
    
    return generated_questions, input_content_begin['messages']

async def process_single_question(question_content, model_client, output_folder, question_index):
    """处理单个问题：变量替换、代码生成、数值优化，并检查合理性"""
    print(f"\n=== 开始处理问题 {question_index} 的数值优化 ===")
    
    max_validation_attempts = 5  # 最大验证尝试次数
    validation_attempt = 0
    is_reasonable = False
    
    current_python_code = None
    current_code_output = None
    
    while validation_attempt < max_validation_attempts and not is_reasonable:
        validation_attempt += 1
        print(f"\n--- 问题 {question_index} - 第 {validation_attempt} 次合理性验证 ---")
        
        # 第一步：生成变量替换的代码
        if validation_attempt == 1:
            # 第一次尝试：生成初始代码
            code_generation_prompt = f"""
            <question>{question_content}</question>
            我想生成多道类似的题目，但是随意设置题目中的数据不一定会存在合理且有实际意义的解。因此，请你将上述题目中的所有数字用规范命名的变量替换(代码中进行注释)，为每个变量赋予合理的取值范围用random库随机取值，生成python代码解出两组各变量的合理赋值，中间结果和问题在这个赋值下的最终答案。如果问题有多个小问，需先仔细判断各小问间是否相互独立或者相互联系。
            请注意设置最大尝试时间，避免代码陷入死循环。
            生成规范注释的python代码以下述格式返回：
            # code begin
            <生成的python代码>
            # code end
            """
        else:
            # 后续尝试：基于前一次的不合理原因修正代码
            code_generation_prompt = f"""
            <question>{question_content}</question>
            <code output>{current_code_output}</code output>
            <The code for generating the answer>{current_python_code}</The code for generating the answer>
            思考导致python代码未成功运行的原因，并修改python代码。
            生成的python代码以下述格式返回：
            # code begin
            <生成的python代码>
            # code end
            """
        
        code_conversation = [
            {"role": "user", "content": code_generation_prompt}
        ]
        
        try:
            # 获取代码生成响应
            code_response = await model_client.text2text({"messages": code_conversation})
            
            if isinstance(code_response, dict) and 'content' in code_response:
                code_content = code_response['content']
            else:
                code_content = str(code_response)
            
            # 提取Python代码
            python_code = extract_python_code(code_content)
            
            if not python_code:
                print(f"问题 {question_index} - 第{validation_attempt}次验证: 未找到Python代码")
                if validation_attempt == max_validation_attempts:
                    return question_content
                continue
            
            current_python_code = python_code
            
            # 保存生成的代码
            code_file = os.path.join(output_folder, f"question_{question_index}_validation_{validation_attempt}_code.py")
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(python_code)
            print(f"问题 {question_index} - 第{validation_attempt}次验证的代码已保存到: {code_file}")
            
            # 第二步：运行Python代码
            print(f"问题 {question_index} - 第{validation_attempt}次验证: 正在运行生成的代码...")
            success, error_info, code_output = run_python_code(python_code)
            
            if not code_output:
                print(f"问题 {question_index} - 第{validation_attempt}次验证: 代码运行无输出或出错")
                if validation_attempt == max_validation_attempts:
                    print(f"问题 {question_index} - 未能生成合理的变量取值，使用原始内容")
                    return question_content
                continue
            
            current_code_output = code_output
            
            # 保存代码输出
            output_file = os.path.join(output_folder, f"question_{question_index}_validation_{validation_attempt}_output.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(code_output)
            print(f"问题 {question_index} - 第{validation_attempt}次验证的代码输出已保存到: {output_file}")
            if success==0:
                continue
            # 第三步：检查变量取值合理性
            validation_prompt = f"""
            <question>{question_content}</question>
            <code output>{code_output}</code output>
            <The code for generating the answer>{python_code}</The code for generating the answer>
            如果python代码输出表示未在最大尝试时间内找到满足条件的解或代码运行存在问题则回答否，否则评估由上述python代码输出的数学问题的各变量取值中，是否存在一组合理且有实际意义的取值（包含题目参数，中间结果及答案），只回答是或否。
            以下述格式回答：
            # anlysis begin
            合理性: <是/否>
            原因：<原因>
            # anlysis end
            """

            validation_conversation = [
                {"role": "user", "content": validation_prompt}
            ]
            
            # 获取合理性评估响应
            validation_response = await model_client.text2text({"messages": validation_conversation})
            
            if isinstance(validation_response, dict) and 'content' in validation_response:
                validation_content = validation_response['content']
            else:
                validation_content = str(validation_response)
            
            # 保存验证输出
            validation_file = os.path.join(output_folder, f"question_{question_index}_validation_{validation_attempt}_result.txt")
            with open(validation_file, 'w', encoding='utf-8') as f:
                f.write(validation_content)
            print(f"问题 {question_index} - 第{validation_attempt}次验证结果已保存到: {validation_file}")
            
            # 解析验证结果
            is_reasonable = "合理性: 是" in validation_content
            
            if is_reasonable:
                print(f"✅ 问题 {question_index} - 第{validation_attempt}次验证: 变量取值合理")
                break
            else:
                print(f"❌ 问题 {question_index} - 第{validation_attempt}次验证: 变量取值不合理")
                print(f"不合理原因: {validation_content}")
                
                if validation_attempt == max_validation_attempts:
                    print(f"⚠️ 问题 {question_index} - 已达到最大验证次数，使用最后一次生成的代码")
                
        except Exception as e:
            print(f"问题 {question_index} - 第{validation_attempt}次验证过程中出错: {str(e)}")
            if validation_attempt == max_validation_attempts:
                return question_content
    
    # 第四步：使用最终验证通过的代码输出生成最终问题
    if is_reasonable and current_code_output and current_python_code:
        print(f"\n=== 问题 {question_index} - 生成最终问题 ===")
        
        question_generation_prompt = f"""
        使用以下Python代码输出中的各变量赋值替换掉原始题目中的数值：
        
        <python代码输出>
        {current_code_output}
        </python代码输出>
        
        原始题目：
        <question>
        {question_content}
        </question>
        
        请以下述格式输出：
        # question begin
        <生成的question>
        # question end
        """
        
        question_conversation = [
            {"role": "user", "content": question_generation_prompt}
        ]
        
        try:
            # 获取最终问题生成响应
            final_response = await model_client.text2text({"messages": question_conversation})
            
            if isinstance(final_response, dict) and 'content' in final_response:
                final_content = final_response['content']
            else:
                final_content = str(final_response)
            
            # 提取最终问题内容
            final_question = extract_final_question(final_content)
            
            if final_question:
                # 保存最终问题
                final_file = os.path.join(output_folder, f"question_{question_index}_final.txt")
                with open(final_file, 'w', encoding='utf-8') as f:
                    f.write(final_question)
                print(f"问题 {question_index} - 最终问题已保存到: {final_file}")
                
                # 保存最终代码和输出
                final_code_file = os.path.join(output_folder, f"question_{question_index}_final_code.py")
                with open(final_code_file, 'w', encoding='utf-8') as f:
                    f.write(current_python_code)
                
                final_output_file = os.path.join(output_folder, f"question_{question_index}_final_output.txt")
                with open(final_output_file, 'w', encoding='utf-8') as f:
                    f.write(current_code_output)
                
                print(f"问题 {question_index} - 最终代码和输出已保存")
                return final_question
            else:
                print(f"问题 {question_index} - 未找到最终问题，使用原始内容")
                return question_content
                
        except Exception as e:
            print(f"问题 {question_index} - 最终问题生成过程中出错: {str(e)}")
            return question_content
    else:
        print(f"问题 {question_index} - 未能生成合理的变量取值，使用原始内容")
        return question_content

def extract_python_code(text):
    """从文本中提取Python代码块"""
    # 尝试新格式: # code begin ... # code end
    pattern_new = r'# code begin\s*(.*?)\s*# code end'
    matches_new = re.findall(pattern_new, text, re.DOTALL)
    
    if matches_new:
        code_content = matches_new[-1].strip()
        # 如果内容中包含```python代码块，提取其中的内容
        python_code_pattern = r'```python\s*(.*?)\s*```'
        python_code_matches = re.findall(python_code_pattern, code_content, re.DOTALL)
        if python_code_matches:
            return python_code_matches[-1].strip()
        else:
            # 如果没有```python标记，直接使用提取的内容
            return code_content
    
    # 尝试旧格式: ```python ... ```
    pattern_old = r'```python\s*(.*?)\s*```'
    matches_old = re.findall(pattern_old, text, re.DOTALL)
    return matches_old[-1].strip() if matches_old else None

def extract_final_question(text):
    """从文本中提取最终问题内容"""
    pattern = r'# question begin\s*(.*?)\s*# question end'
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[-1].strip() if matches else None

def run_python_code(code):
    """运行Python代码并返回(success, error_info, full_output)三元组"""
    temp_file_path = None
    try:
        # 创建一个临时文件来运行代码
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        # 运行代码
        result = subprocess.run(
            ['python', temp_file_path],
            capture_output=True, 
            text=True, 
            timeout=30,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        
        # 组合输出
        full_output = ""
        if result.stdout:
            full_output += result.stdout
        if result.stderr:
            full_output += f"\n错误信息:\n{result.stderr}"
        
        # 清理临时文件
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except Exception as e:
            print(f"清理临时文件失败: {str(e)}")
        
        # 判断执行是否成功
        success = (result.returncode == 0)
        error_info = None
        
        if success:
            print("Python代码执行成功！")
            return True, None, full_output.strip() if full_output.strip() else "代码运行无输出"
        else:
            # 执行失败，提取错误信息
            error_info = full_output.strip() if full_output.strip() else f"返回码: {result.returncode}, 无错误信息"
            formatted_error = extract_error_info(error_info)
            return False, formatted_error or error_info, full_output
        
    except subprocess.TimeoutExpired:
        # 清理临时文件
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except:
            pass
        return False, "代码执行超时", None
    except Exception as e:
        # 清理临时文件
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except:
            pass
        return False, f"代码执行异常: {str(e)}", None

def prepare_stage_files(generated_questions,question_name, output_folder):
    """准备Stage文件，用生成的问题填充<question>占位符"""
    print(f"\n=== 准备Stage文件，使用 {len(generated_questions)} 个生成的问题 ===")
    
    stage_folder_path = '/mnt/omniSSD/user_workspace/xiongkai/smt-master/prompts/Stage/'
    prepared_stages = []
    question_names = []
    for i, question in enumerate(generated_questions, 1):
        stage_file_path = os.path.join(stage_folder_path, "stage_1.md")
        
        if not os.path.exists(stage_file_path):
            print(f"错误: Stage文件 {stage_file_path} 不存在")
            continue
            
        # 读取stage_1.md内容
        with open(stage_file_path, 'r', encoding='utf-8') as f:
            stage_content = f.read()
        
        # 替换<question>占位符
        stage_content = stage_content.replace('<question>', question)
        stage_content = stage_content.replace('<question_name>', question_name+"_"+str(i-1))
        # 保存准备好的stage内容
        prepared_stage_file = os.path.join(output_folder, f"prepared_stage_1_question_{i}.md")
        with open(prepared_stage_file, 'w', encoding='utf-8') as f:
            f.write(stage_content)
        
        prepared_stages.append(stage_content)
        question_names.append(question_name+"_"+str(i-1))
        print(f"已准备第 {i} 个问题的Stage文件: {prepared_stage_file}")
    
    return prepared_stages, question_names

async def process_stages(total_attempt, base_output_folder, model_name, n=None, original_question=None, question_name=None):
    """处理所有stage的主要逻辑"""
    # 为每次总尝试创建子文件夹
    attempt_folder = os.path.join(base_output_folder, f"attempt_{total_attempt}")
    os.makedirs(attempt_folder, exist_ok=True)

    # 创建模型实例
    ds = DEEPSEEKClient(model=model_name)

    try:
        # 如果提供了n和original_question，先生成相关问题
        generated_questions = None
        polish_conversation = None
        
        if n is not None and original_question is not None:
            generated_questions, polish_conversation = await generate_questions(n, original_question, ds, attempt_folder)
            
            if not generated_questions:
                print("❌ 问题生成失败，无法继续")
                return False, attempt_folder
            
            # 准备Stage文件
            prepared_stages,question_names = prepare_stage_files(generated_questions,question_name, attempt_folder)
            
            if not prepared_stages:
                print("❌ Stage文件准备失败，无法继续")
                return False, attempt_folder
            
            # 处理所有生成的问题
            all_questions_success = True
            final_results = []
            
            for question_idx, prepared_stage in enumerate(prepared_stages, 1):
                print(f"\n{'='*50}")
                print(f"开始处理第 {question_idx}/{len(prepared_stages)} 个问题")
                print(f"{'='*50}")
                
                # 为每个问题创建子文件夹
                question_folder = os.path.join(attempt_folder, f"question_{question_idx}")
                os.makedirs(question_folder, exist_ok=True)
                each_question_name = question_names[question_idx-1]
                # 初始化对话历史
                input_content = {
                    'messages': []
                }
                
                # 使用当前问题的stage内容
                message = {
                    "role": "user",
                    "content": prepared_stage
                }
                input_content['messages'].append(message)
                
                # 发送请求获取模型回复
                try:
                    stage_response = await ds.text2text(input_content)
                    
                    if isinstance(stage_response, dict) and 'content' in stage_response:
                        response_content = stage_response['content']
                    else:
                        response_content = str(stage_response)
                    
                    # 提取当前stage的YAML内容和Python代码
                    yaml_content, python_code = extract_yaml_and_code(response_content)
                    
                    # 保存YAML内容和Python代码到问题子文件夹
                    if yaml_content:
                        output_file = os.path.join(question_folder, f"stage_1_output.yaml")
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(yaml_content)
                        print(f"问题 {question_idx} - Stage 1 的YAML内容已保存到: {output_file}")
                        
                        # 保存Python代码
                        if python_code:
                            code_file = os.path.join(question_folder, f"stage_1_code.py")
                            with open(code_file, 'w', encoding='utf-8') as f:
                                f.write(python_code)
                            print(f"问题 {question_idx} - Stage 1 的Python代码已保存到: {code_file}")
                    else:
                        print(f"问题 {question_idx} - Stage 1 的响应中未找到YAML内容")

                    # 将模型回复添加到对话历史
                    input_content['messages'].append({
                        "role": "assistant", 
                        "content": response_content
                    })
                    
                    print(f"问题 {question_idx} - Stage 1 处理完成")
                    
                except Exception as e:
                    print(f"问题 {question_idx} - Stage 1 处理失败: {str(e)}")
                    all_questions_success = False
                    continue
                
                # 继续处理stage 2-4
                folder_path = '/mnt/omniSSD/user_workspace/xiongkai/smt-master/prompts/Stage/'
                for stage_num in range(2, 5):
                    file_name = f"stage_{stage_num}.md"
                    file_path = os.path.join(folder_path, file_name)
                    
                    if not os.path.exists(file_path):
                        print(f"警告: 文件 {file_path} 不存在")
                        continue
                        
                    # 读取文件内容
                    with open(file_path, 'r', encoding='utf-8') as file:
                        file_content = file.read()
                    
                    message = {
                        "role": "user",
                        "content": file_content
                    }
                    
                    input_content['messages'].append(message)
                    
                    # 发送请求获取模型回复
                    try:
                        stage_response = await ds.text2text(input_content)
                        
                        if isinstance(stage_response, dict) and 'content' in stage_response:
                            response_content = stage_response['content']
                        else:
                            response_content = str(stage_response)
                        
                        # 提取当前stage的YAML内容和Python代码
                        yaml_content, python_code = extract_yaml_and_code(response_content)
                        
                        # 保存YAML内容和Python代码到问题子文件夹
                        if yaml_content:
                            output_file = os.path.join(question_folder, f"stage_{stage_num}_output.yaml")
                            with open(output_file, 'w', encoding='utf-8') as f:
                                f.write(yaml_content)
                            print(f"问题 {question_idx} - Stage {stage_num} 的YAML内容已保存到: {output_file}")
                            
                            # 保存Python代码
                            if python_code:
                                code_file = os.path.join(question_folder, f"stage_{stage_num}_code.py")
                                with open(code_file, 'w', encoding='utf-8') as f:
                                    f.write(python_code)
                                print(f"问题 {question_idx} - Stage {stage_num} 的Python代码已保存到: {code_file}")
                        else:
                            print(f"问题 {question_idx} - Stage {stage_num} 的响应中未找到YAML内容")
                        
                        # 将模型回复添加到对话历史
                        input_content['messages'].append({
                            "role": "assistant", 
                            "content": response_content
                        })
                        
                    except Exception as e:
                        print(f"问题 {question_idx} - Stage {stage_num} 处理失败: {str(e)}")
                        all_questions_success = False
                        break
                
                # 对当前问题的最后一个stage的YAML进行测试和修正
                print(f"\n=== 开始测试和修正问题 {question_idx} 的YAML ===")
                question_success, question_result = await process_single_question_yaml(
                    input_content, question_idx, question_folder, ds, each_question_name
                )
                
                final_results.append({
                    'question_index': question_idx,
                    'success': question_success,
                    'folder': question_folder
                })
                
                if not question_success:
                    all_questions_success = False
            
            # 返回整体结果
            success_count = sum(1 for result in final_results if result['success'])
            print(f"\n{'='*50}")
            print(f"所有问题处理完成: {success_count}/{len(prepared_stages)} 个成功")
            print(f"{'='*50}")
            
            return all_questions_success, attempt_folder

        else:
            # 原始逻辑：没有生成问题的情况
            print("使用原始处理逻辑（无生成问题）")
            # ... 保留原有的处理逻辑
            
            return False, attempt_folder

    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        return False, attempt_folder
    finally:
        # 确保正确关闭模型连接
        await ds.close()

async def process_single_question_yaml(input_content, question_idx, question_folder, model_client, each_question_name):
    """处理单个问题的YAML测试和修正"""
    max_attempts = 10
    attempt_count = 0
    success = False
    translator_output = None

    while attempt_count < max_attempts and not success:
        attempt_count += 1
        print(f"\n=== 问题 {question_idx} - 第 {attempt_count} 次调试尝试 ===")
        
        # 从最后一次模型回复中提取YAML和Python代码
        last_response = input_content['messages'][-1]['content']
        yaml_content, python_code = extract_yaml_and_code(last_response)
        
        if not yaml_content:
            print(f"问题 {question_idx} - 未找到YAML内容，无法进行测试")
            break
        
        # 测试YAML文件
        success, error_info, translator_output = save_yaml_and_code(yaml_content, python_code, attempt_count, question_folder, each_question_name)
        
        if not success:
            print(f"问题 {question_idx} - 运行失败，错误信息: {error_info}")
            
            # 保存当前错误信息
            error_file = os.path.join(question_folder, f"debug_attempt_{attempt_count}_error.txt")
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(error_info)
            print(f"错误信息已保存到: {error_file}")
            
            if attempt_count < max_attempts:
                # 构建修正请求
                correction_prompt = {
                    "role": "user",
                    "content": f"""报错信息如下：
                        {error_info}
                        思考可能的原因,按下述格式输出修改后的yaml文件。
                        #### final yaml begin
                        <生成的yaml文件>
                        #### final yaml end
                        #### final code begin
                        <生成的python文件>
                        #### final code end
                        """
                }
                
                # 添加修正请求到对话历史
                input_content['messages'].append(correction_prompt)
                
                try:
                    # 获取修正后的YAML
                    correction_response = await model_client.text2text(input_content)
                    
                    # 检查返回类型
                    if isinstance(correction_response, dict) and 'content' in correction_response:
                        correction_content = correction_response['content']
                    else:
                        correction_content = str(correction_response)
                    
                    # 保存完整的修正输出
                    save_full_output(correction_content, f"debug_attempt_{attempt_count}_full_output.txt", question_folder)
                    
                    # 提取修正后的YAML内容和Python代码
                    corrected_yaml_content, corrected_python_code = extract_yaml_and_code(correction_content)
                    
                    # 保存修正后的YAML文件和Python代码
                    if corrected_yaml_content:
                        corrected_output_file = os.path.join(question_folder, f"debug_attempt_{attempt_count}.yaml")
                        with open(corrected_output_file, 'w', encoding='utf-8') as f:
                            f.write(corrected_yaml_content)
                        print(f"问题 {question_idx} - 第{attempt_count}次修正的YAML已保存到: {corrected_output_file}")
                        
                        # 保存Python代码
                        if corrected_python_code:
                            corrected_code_file = os.path.join(question_folder, f"debug_attempt_{attempt_count}.py")
                            with open(corrected_code_file, 'w', encoding='utf-8') as f:
                                f.write(corrected_python_code)
                            print(f"问题 {question_idx} - 第{attempt_count}次修正的Python代码已保存到: {corrected_code_file}")
                    
                    # 将修正回复添加到对话历史
                    input_content['messages'].append({
                        "role": "assistant", 
                        "content": correction_content
                    })
                    
                    print(f"问题 {question_idx} - 已请求模型修正YAML文件")
                    time.sleep(1)  # 避免请求过于频繁
                    
                except Exception as e:
                    print(f"问题 {question_idx} - 修正请求失败: {str(e)}")
                    break
        else:
            print(f"问题 {question_idx} - YAML文件测试成功！")
            # 保存最终的YAML文件和Python代码
            final_output_file = os.path.join(question_folder, "final_corrected_output.yaml")
            with open(final_output_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            print(f"问题 {question_idx} - 最终修正的YAML文件已保存为: {final_output_file}")
            
            # 保存最终的Python代码
            if python_code:
                final_code_file = os.path.join(question_folder, "final_corrected_code.py")
                with open(final_code_file, 'w', encoding='utf-8') as f:
                    f.write(python_code)
                print(f"问题 {question_idx} - 最终修正的Python代码已保存为: {final_code_file}")
            
            # 保存translator输出
            if translator_output:
                translator_output_file = os.path.join(question_folder, "translator_output.txt")
                with open(translator_output_file, 'w', encoding='utf-8') as f:
                    f.write(translator_output)
                print(f"问题 {question_idx} - Translator输出已保存为: {translator_output_file}")
            
            # 进入模型评估阶段
            print(f"\n=== 开始问题 {question_idx} 的模型评估阶段 ===")
            model_eval_times = 5
            eval_attempt = 0
            problem_valid = False
            
            while eval_attempt < model_eval_times and not problem_valid and translator_output:
                eval_attempt += 1
                print(f"\n=== 问题 {question_idx} - 第 {eval_attempt} 次模型评估 ===")
                # 评估问题合理性
                problem_valid, invalid_reason, eval_response = await evaluate_problem_validity(
                    translator_output, model_client, input_content['messages'], question_folder, eval_attempt
                )
                if problem_valid:
                    print(f"✅ 问题 {question_idx} - 模型评估通过：生成的数学问题合理，保存至final_corrected_output.yaml")
                    return True, question_folder
                else:
                    print(f"❌ 问题 {question_idx} - 模型评估未通过：{invalid_reason}")
                    
                    if eval_attempt < model_eval_times:
                        # 构建基于评估结果的修正请求
                        eval_correction_prompt = {
                            "role": "user",
                            "content": f"""{invalid_reason},思考可能的原因,按下述格式输出修改后的yaml文件。
                        #### final yaml begin
                        <生成的yaml文件>
                        #### final yaml end
                        #### final code begin
                        <生成的python文件>
                        #### final code end
                        """
                        }
                        
                        # 添加修正请求到对话历史
                        input_content['messages'].append(eval_correction_prompt)
                        
                        try:
                            # 获取修正后的YAML
                            eval_correction_response = await model_client.text2text(input_content)
                            
                            # 检查返回类型
                            if isinstance(eval_correction_response, dict) and 'content' in eval_correction_response:
                                eval_correction_content = eval_correction_response['content']
                            else:
                                eval_correction_content = str(eval_correction_response)
                            
                            # 保存完整的修正输出
                            save_full_output(eval_correction_content, f"eval_correction_attempt_{eval_attempt}_output.txt", question_folder)
                            
                            # 提取修正后的YAML内容和Python代码
                            corrected_yaml_content, corrected_python_code = extract_yaml_and_code(eval_correction_content)
                            
                            if not corrected_yaml_content:
                                print(f"问题 {question_idx} - 修正响应中未找到YAML内容，继续下一次评估")
                                continue
                            
                            # 保存修正后的YAML文件和Python代码
                            corrected_output_file = os.path.join(question_folder, f"eval_correction_attempt_{eval_attempt}.yaml")
                            with open(corrected_output_file, 'w', encoding='utf-8') as f:
                                f.write(corrected_yaml_content)
                            with open(os.path.join(question_folder, "final_corrected_output.yaml"), 'w', encoding='utf-8') as f:
                                f.write(corrected_yaml_content)
                            print(f"问题 {question_idx} - 第{eval_attempt}次评估修正的YAML已保存到: {corrected_output_file}")
                            
                            # 保存Python代码
                            if corrected_python_code:
                                corrected_code_file = os.path.join(question_folder, f"eval_correction_attempt_{eval_attempt}.py")
                                with open(corrected_code_file, 'w', encoding='utf-8') as f:
                                    f.write(corrected_python_code)
                                with open(os.path.join(question_folder, "final_corrected_code.py"), 'w', encoding='utf-8') as f:
                                    f.write(corrected_python_code)
                                print(f"问题 {question_idx} - 第{eval_attempt}次评估修正的Python代码已保存到: {corrected_code_file}")
                            
                            # 将修正回复添加到对话历史
                            input_content['messages'].append({
                                "role": "assistant", 
                                "content": eval_correction_content
                            })
                            
                            # 保存当前对话历史
                            save_conversation_history(input_content['messages'], f"eval_correction_attempt_{eval_attempt}_conversation.json", question_folder)
                            
                            # 重新测试修正后的YAML
                            print(f"问题 {question_idx} - 重新测试修正后的YAML...")
                            success, error_info, translator_output = save_yaml_and_code(
                                corrected_yaml_content, corrected_python_code, f"eval_{eval_attempt}", question_folder, each_question_name
                            )
                            
                            if not success:
                                print(f"问题 {question_idx} - 重新测试失败: {error_info}")
                                # 这里可以添加debug循环，但为了简洁先跳过
                                continue
                            
                        except Exception as e:
                            print(f"问题 {question_idx} - 评估修正请求失败: {str(e)}")
                            continue
                    else:
                        print(f"问题 {question_idx} - 已达到最大评估次数 ({model_eval_times})，停止评估")
            
            # 如果评估阶段结束但问题仍不合理
            if not problem_valid:
                print(f"❌ 问题 {question_idx} - 经过评估阶段后，生成的数学问题仍不合理")
                #return False, question_folder
                success = False  # 关键：重置成功状态

    if not success and attempt_count >= max_attempts:
        print(f"\n问题 {question_idx} - 经过 {max_attempts} 次调试尝试仍未修正成功")
        
        # 保存最后一次修正的YAML文件和Python代码
        last_attempt_file = os.path.join(question_folder, "last_debug_attempt.yaml")
        last_response = input_content['messages'][-1]['content']
        last_yaml_content, last_python_code = extract_yaml_and_code(last_response)
        if last_yaml_content:
            with open(last_attempt_file, 'w', encoding='utf-8') as f:
                f.write(last_yaml_content)
            print(f"问题 {question_idx} - 最后一次修正的YAML已保存到: {last_attempt_file}")
            
            # 保存Python代码
            if last_python_code:
                last_code_file = os.path.join(question_folder, "last_debug_attempt.py")
                with open(last_code_file, 'w', encoding='utf-8') as f:
                    f.write(last_python_code)
                print(f"问题 {question_idx} - 最后一次修正的Python代码已保存到: {last_code_file}")
        
        # 保存最终对话历史
        save_conversation_history(input_content['messages'], "final_conversation.json", question_folder)
    
    return success, question_folder

async def main_async():
    """异步主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='数学问题转换和评估工具')
    parser.add_argument('-n', type=int, help='要生成的数学问题数量')
    parser.add_argument('-question', type=str, help='原始数学问题')
    parser.add_argument('-question_name', type=str, help='问题名称') 
    args = parser.parse_args()
    
    # 创建主输出文件夹
    base_output_folder = "stage_output"
    os.makedirs(base_output_folder, exist_ok=True)
    
    total_max_attempts = 1
    total_attempt = 1
    overall_success = False
    successful_attempt_folder = ""
    model_V3_1 = "ep-20250822145246-jc6j8"
    
    try:
        while total_attempt <= total_max_attempts and not overall_success:
            print(f"\n{'='*60}")
            print(f"开始第 {total_attempt} 次总尝试 (共 {total_max_attempts} 次)")
            print(f"{'='*60}")
            
            # 传递参数给process_stages
            overall_success, attempt_folder = await process_stages(
                total_attempt, base_output_folder, model_V3_1, 
                n=args.n, original_question=args.question, question_name=args.question_name
            )
            
            if overall_success:
                successful_attempt_folder = attempt_folder
                print(f"\n🎉 成功！在第 {total_attempt} 次总尝试中完成转换")
                # 在根目录创建一个成功的标记文件
                success_marker = os.path.join(base_output_folder, "SUCCESS.txt")
                with open(success_marker, 'w', encoding='utf-8') as f:
                    f.write(f"转换成功于第 {total_attempt} 次尝试\n")
                    f.write(f"成功文件夹: {attempt_folder}\n")
                    f.write(f"完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            else:
                print(f"\n❌ 第 {total_attempt} 次总尝试失败")
                total_attempt += 1
                
                if total_attempt <= total_max_attempts:
                    print("准备开始下一次总尝试...")
                    time.sleep(2)  # 等待一段时间再开始下一次尝试
        
        if not overall_success:
            print(f"\n{'='*60}")
            print(f"❌ 经过 {total_max_attempts} 次总尝试仍未成功完成转换")
            print("无法成功转换")
            
            # 在根目录创建一个失败的标记文件
            failure_marker = os.path.join(base_output_folder, "FAILURE.txt")
            with open(failure_marker, 'w', encoding='utf-8') as f:
                f.write(f"经过 {total_max_attempts} 次尝试仍未成功转换\n")
                f.write(f"最后尝试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print(f"{'='*60}")
            return False
        else:
            print(f"\n{'='*60}")
            print("✅ 所有处理完成！")
            print(f"成功转换的YAML文件位于: {successful_attempt_folder}")
            print(f"{'='*60}")
            return True
            
    except Exception as e:
        print(f"主程序执行出错: {str(e)}")
        return False


def main():
    """主函数"""
    try:
        success = asyncio.run(main_async())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()