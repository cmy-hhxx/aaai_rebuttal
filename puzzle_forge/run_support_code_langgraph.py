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
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

Path = "/mnt/omniSSD/user_workspace/xiongkai/llm_general_r1/llm-eval/tools/"
sys.path.append(Path)
from ExternalApi import DEEPSEEKClient, GPT5Client

# 定义状态类型
class WorkflowState(TypedDict):
    # 输入参数
    n: int
    original_question: str
    question_name: str
    generate_questions: bool
    model_eval_final: bool
    data_augment: bool
    workspace: str
    output_folder: str
    model_name: str
    
    # 处理状态
    current_stage: str
    attempt_count: int
    total_attempt: int
    max_attempts: int
    debug_times: int
    need_data_augment: bool
    
    # 数据存储
    generated_questions: List[str]
    question_names: List[str]
    prepared_stages: List[str]
    current_question_index: int
    current_yaml_content: Optional[str]
    current_python_code: Optional[str]
    translator_output: Optional[str]
    error_info: Optional[str]
    success_list: List[str]
    
    # 输出路径
    base_output_folder: str
    current_attempt_folder: str
    current_question_folder: str
    
    # 模型客户端
    model_client: Any
    conversation_history: List[Dict[str, str]]


class MathProblemWorkflow:
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """构建工作流图"""
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("initialize", self.initialize)
        workflow.add_node("generate_questions", self.generate_questions)
        workflow.add_node("prepare_stages", self.prepare_stages)
        workflow.add_node("setup_question", self.setup_question)  # 新增：设置问题环境
        workflow.add_node("extract_yaml_code", self.extract_yaml_code)
        workflow.add_node("test_yaml", self.test_yaml)
        workflow.add_node("debug_yaml", self.debug_yaml)
        workflow.add_node("check_data_augment", self.check_data_augment)
        workflow.add_node("data_augmentation", self.data_augmentation)
        workflow.add_node("evaluate_problem", self.evaluate_problem)
        workflow.add_node("finalize", self.finalize)
        
        # 设置入口点
        workflow.set_entry_point("initialize")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "initialize",
            self.should_generate_questions,
            {
                "generate": "generate_questions",
                "skip": "prepare_stages"
            }
        )
        
        workflow.add_edge("generate_questions", "prepare_stages")
        workflow.add_edge("prepare_stages", "setup_question")
        
        workflow.add_conditional_edges(
            "setup_question",
            self.has_more_questions,
            {
                "continue": "extract_yaml_code",
                "done": "finalize"
            }
        )
        
        workflow.add_edge("extract_yaml_code", "test_yaml")
        
        workflow.add_conditional_edges(
            "test_yaml",
            self.test_result_condition,
            {
                "success": "check_data_augment",
                "debug": "debug_yaml",
                "fail": "setup_question"  # 失败时回到setup_question，会自动递增索引
            }
        )
        
        workflow.add_conditional_edges(
            "debug_yaml",
            self.debug_condition,
            {
                "retry": "test_yaml",
                "fail": "setup_question"  # 调试失败时回到setup_question
            }
        )
        
        workflow.add_conditional_edges(
            "check_data_augment",
            self.augmentation_condition,
            {
                "augment": "data_augmentation",
                "skip": "evaluate_problem"
            }
        )
        
        workflow.add_edge("data_augmentation", "test_yaml")  # 增强后重新测试
        
        workflow.add_conditional_edges(
            "evaluate_problem",
            self.evaluation_condition,
            {
                "success": "setup_question",  # 评估成功，处理下一个问题
                "retry": "extract_yaml_code",  # 评估失败，重新提取YAML和代码，然后测试
                "skip": "setup_question"      # 跳过评估，处理下一个问题
            }
        )
        
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    # 条件判断函数
    def should_generate_questions(self, state: WorkflowState) -> str:
        if state["generate_questions"] and state["n"] > 0 and state["original_question"]:
            return "generate"
        return "skip"
    
    def has_more_questions(self, state: WorkflowState) -> str:
        if state["current_question_index"] < len(state["prepared_stages"]):
            return "continue"
        return "done"
    
    def test_result_condition(self, state: WorkflowState) -> str:
        if state.get("error_info") is None and state.get("translator_output"):
            return "success"
        elif state["attempt_count"] < state["max_attempts"]:
            return "debug"
        return "fail"  # 超过最大尝试次数，放弃这道题

    
    def debug_condition(self, state: WorkflowState) -> str:
        if state["current_yaml_content"] and state["attempt_count"] < state["max_attempts"]:
            return "retry"
        return "fail"  # 没有YAML内容或超过最大尝试次数
    
    def augmentation_condition(self, state: WorkflowState) -> str:
        # 只有在YAML测试成功且需要数据增强时才执行
        if state["data_augment"] and state["need_data_augment"]:
            return "augment"
        return "skip"
    
    def evaluation_condition(self, state: WorkflowState) -> str:
        """评估结果条件判断"""
        if not state["model_eval_final"]:
            return "skip"
        
        # 如果有错误信息且包含"评估不通过"，说明需要重新提取和测试
        if state.get("error_info") and "评估不通过" in state["error_info"]:
            return "retry"  # 返回extract_yaml_code重新提取和测试
        
        # 如果评估通过且没有错误，继续下一个问题
        if state.get("error_info") is None:
            return "success"
        
        return "retry"
    
    # 节点函数
    async def initialize(self, state: WorkflowState) -> WorkflowState:
        """初始化工作流"""
        print(f"\n{'='*60}")
        print(f"开始第 {state['total_attempt']} 次总尝试")
        print(f"{'='*60}")
        
        # 创建输出文件夹
        attempt_folder = os.path.join(state["base_output_folder"], f"attempt_{state['total_attempt']}")
        os.makedirs(attempt_folder, exist_ok=True)
        
        # 初始化模型客户端
        model_client = GPT5Client()
        
        return {
            **state,
            "current_attempt_folder": attempt_folder,
            "model_client": model_client,
            "conversation_history": [],
            "generated_questions": [],
            "question_names": [],
            "prepared_stages": [],
            "current_question_index": 0,
            "attempt_count": 0,
            "debug_times": 0,
            "success_list": [],
            "need_data_augment": True  # 初始需要数据增强
        }
    
    async def generate_questions(self, state: WorkflowState) -> WorkflowState:
        """生成相关问题"""
        print(f"\n=== 开始生成 {state['n']} 个相关数学问题 ===")
        
        # 将原始问题添加为question_0
        generated_questions = [state["original_question"]]
        
        # 读取Polish阶段文件
        polish_folder_path = os.path.join(state["workspace"], 'prompts/Stage_Polish/')
        if state["model_client"] is not None:
            input_content = {'messages': []}
        else:
            input_content = {'prompt': {'messages': []}}
        
        # 处理Polish阶段
        for i in range(1, 3):  # stage_1.md 到 stage_2.md
            file_path = os.path.join(polish_folder_path, f"stage_{i}.md")
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
            
            file_content = file_content.replace('<n>', str(state["n"]))
            file_content = file_content.replace('<question>', state["original_question"])
            
            message = {"role": "user", "content": file_content}
            if state["model_client"] is not None:
                input_content['messages'].append(message)
            else:
                input_content['prompt']['messages'].append(message)
            
            try:
                if state["model_client"] is not None:
                    response = await state["model_client"].text2text(input_content)
                    response_content = response['content'] if isinstance(response, dict) and 'content' in response else str(response)
                    input_content['messages'].append({"role": "assistant", "content": response_content})
                else:
                    response = requests.post('http://10.244.31.40:6667/model', json=input_content).json()['output']
                    response_content = response['content'] if isinstance(response, dict) and 'content' in response else str(response)
                    input_content['prompt']['messages'].append({"role": "assistant", "content": response_content})
                
                print(f"Polish Stage {i} 处理完成")
                
            except Exception as e:
                print(f"Polish Stage {i} 处理失败: {str(e)}")
                return state
        
        # 提取生成的问题
        if state["model_client"] is not None:
            last_response = input_content['messages'][-1]['content']
        else:
            last_response = input_content['prompt']['messages'][-1]['content']
        
        for i in range(1, state["n"] + 1):
            question_content = self.extract_question_content(last_response, i)
            if question_content:
                generated_questions.append(question_content)
        
        # 保存生成的问题
        question_folder = os.path.join(state["current_attempt_folder"], "generated_questions")
        os.makedirs(question_folder, exist_ok=True)
        
        for i, question in enumerate(generated_questions):
            question_file = os.path.join(question_folder, f"question_{i}.txt")
            with open(question_file, 'w', encoding='utf-8') as f:
                f.write(question)
        
        # 保存对话历史
        conversation_file = os.path.join(state["current_attempt_folder"], "polish_conversation.json")
        with open(conversation_file, 'w', encoding='utf-8') as f:
            if state["model_client"] is not None:
                json.dump(input_content['messages'], f, ensure_ascii=False, indent=2)
            else:
                json.dump(input_content['prompt']['messages'], f, ensure_ascii=False, indent=2)
        
        return {
            **state,
            "generated_questions": generated_questions,
            "conversation_history": input_content['messages'] if state["model_client"] is not None else input_content['prompt']['messages']
        }
    
    async def prepare_stages(self, state: WorkflowState) -> WorkflowState:
        """准备Stage文件"""
        questions = state["generated_questions"] if state["generated_questions"] else [state["original_question"]]
        print(f"\n=== 准备Stage文件，使用 {len(questions)} 个问题 ===")
        
        stage_folder_path = os.path.join(state["workspace"], 'prompts/Stage/')
        prepared_stages = []
        question_names = []
        
        for i, question in enumerate(questions):
            stage_file_path = os.path.join(stage_folder_path, "stage_1.md")
            if not os.path.exists(stage_file_path):
                continue
                
            with open(stage_file_path, 'r', encoding='utf-8') as f:
                stage_content = f.read()
            
            stage_content = stage_content.replace('<question>', question)
            stage_content = stage_content.replace('<question_name>', f"{state['question_name']}_{i}")
            
            prepared_stage_file = os.path.join(state["current_attempt_folder"], f"prepared_stage_1_question_{i+1}.md")
            with open(prepared_stage_file, 'w', encoding='utf-8') as f:
                f.write(stage_content)
            
            prepared_stages.append(stage_content)
            question_names.append(f"{state['question_name']}_{i}")
        
        return {
            **state,
            "prepared_stages": prepared_stages,
            "question_names": question_names
        }
    
    async def setup_question(self, state: WorkflowState) -> WorkflowState:
        """设置当前问题环境"""
        # 检查是否还有更多问题要处理
        if state["current_question_index"] >= len(state["prepared_stages"]):
            return state
        
        question_idx = state["current_question_index"] + 1
        print(f"\n{'='*50}")
        print(f"开始处理第 {question_idx}/{len(state['prepared_stages'])} 个问题")
        print(f"{'='*50}")
        
        # 创建问题子文件夹
        question_folder = os.path.join(state["current_attempt_folder"], f"question_{question_idx}")
        os.makedirs(question_folder, exist_ok=True)
        
        # 只有在处理新问题时才重置attempt_count
        # 如果current_question_folder已经设置且与当前要设置的不同，说明是新问题
        is_new_question = (
            "current_question_folder" not in state or 
            state["current_question_folder"] != question_folder
        )
        
        return {
            **state,
            "current_question_folder": question_folder,
            "attempt_count": 0 if is_new_question else state["attempt_count"],  # 新题重置，同题保持
            "need_data_augment": True,
            "error_info": None,
            "translator_output": None
        }
    
    async def extract_yaml_code(self, state: WorkflowState) -> WorkflowState:
        """提取YAML和Python代码"""
        # 首先检查是否是从评估失败过来的重试
        is_eval_retry = state.get("error_info") and "评估不通过" in state["error_info"]
        
        if not is_eval_retry:
            # 正常处理：调用模型处理当前问题
            prepared_stage = state["prepared_stages"][state["current_question_index"]]
            if state["model_client"] is not None:
                input_content = {'messages': [{"role": "user", "content": prepared_stage}]}
            else:
                input_content = {'prompt': {'messages': [{"role": "user", "content": prepared_stage}]}}
            
            try:
                if state["model_client"] is not None:
                    response = await state["model_client"].text2text(input_content)
                    response_content = response['content'] if isinstance(response, dict) and 'content' in response else str(response)
                    input_content['messages'].append({"role": "assistant", "content": response_content})
                else:
                    response = requests.post('http://10.244.31.40:6667/model', json=input_content).json()['output']
                    response_content = response['content'] if isinstance(response, dict) and 'content' in response else str(response)
                    input_content['prompt']['messages'].append({"role": "assistant", "content": response_content})
                
                # 保存响应
                output_file = os.path.join(state["current_question_folder"], "stage_1_response.txt")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(response_content)
                
                # 提取YAML和代码
                yaml_content, python_code = self.extract_yaml_and_code(response_content)
                
                return {
                    **state,
                    "conversation_history": input_content['messages'] if state["model_client"] is not None else input_content['prompt']['messages'],
                    "current_yaml_content": yaml_content,
                    "current_python_code": python_code,
                    "error_info": None,
                    "translator_output": None
                }
                
            except Exception as e:
                print(f"问题处理失败: {str(e)}")
                # 处理失败时递增索引
                return {
                    **state,
                    "current_question_index": state["current_question_index"] + 1,
                    "error_info": f"问题处理失败: {str(e)}"
                }
        else:
            # 评估失败的重试：使用现有的对话历史，从最后一条消息提取YAML
            if state["model_client"] is not None:
                last_response = state["conversation_history"][-1]['content']
            else:
                last_response = state["conversation_history"][-1]['content']
            
            yaml_content, python_code = self.extract_yaml_and_code(last_response)
            
            return {
                **state,
                "current_yaml_content": yaml_content,
                "current_python_code": python_code,
                "error_info": None,
                "translator_output": None
            }
    
    async def test_yaml(self, state: WorkflowState) -> WorkflowState:
        """测试YAML文件"""
        if not state["current_yaml_content"]:
            return {**state, "error_info": "没有YAML内容可测试"}
        
        success, error_info, translator_output = self.save_yaml_and_code(
            state["current_yaml_content"],
            state["current_python_code"],
            state["attempt_count"] + 1,
            state["current_question_folder"],
            state["question_names"][state["current_question_index"]],
            state["workspace"]
        )
        
        state_updates = {
            "attempt_count": state["attempt_count"] + 1,
            "error_info": error_info,
            "translator_output": translator_output
        }
        
        if success:
            # 保存最终的YAML文件和Python代码
            final_output_file = os.path.join(state["current_question_folder"], "final_corrected_output.yaml")
            with open(final_output_file, 'w', encoding='utf-8') as f:
                f.write(state["current_yaml_content"])
            print(f"最终修正的YAML文件已保存为: {final_output_file}")
            
            # 保存最终的Python代码
            if state["current_python_code"]:
                final_code_file = os.path.join(state["current_question_folder"], "final_corrected_code.py")
                with open(final_code_file, 'w', encoding='utf-8') as f:
                    f.write(state["current_python_code"])
                print(f"最终修正的Python代码已保存为: {final_code_file}")
            
            # 保存translator输出
            if translator_output:
                translator_output_file = os.path.join(state["current_question_folder"], "translator_output.txt")
                with open(translator_output_file, 'w', encoding='utf-8') as f:
                    f.write(translator_output)
                print(f"Translator输出已保存为: {translator_output_file}")
            
            # 只有在不需要数据增强和模型评估时才立即添加到成功列表
            if not state["data_augment"] and not state["model_eval_final"]:
                state_updates["success_list"] = state["success_list"] + [state["question_names"][state["current_question_index"]]]
                state_updates["debug_times"] = state["debug_times"] + state["attempt_count"]
        
        return {**state, **state_updates}
    
    async def debug_yaml(self, state: WorkflowState) -> WorkflowState:
        """调试YAML文件"""
        if not state["error_info"]:
            return state
        
        print(f"问题调试 - 错误信息: {state['error_info']}")
        
        # 构建修正请求
        correction_prompt = {
            "role": "user",
            "content": f"""报错信息如下：
                {state['error_info']}
                思考可能的原因,按下述格式输出修改后的yaml文件。
                #### final yaml begin
                <生成的yaml文件>
                #### final yaml end
                #### final code begin
                <生成的python文件>
                #### final code end
                """
        }
        
        if state["model_client"] is not None:
            new_messages = state["conversation_history"] + [correction_prompt]
            input_content = {'messages': new_messages}
        else:
            new_messages = state["conversation_history"] + [correction_prompt]
            input_content = {'prompt': {'messages': new_messages}}
        
        try:
            if state["model_client"] is not None:
                response = await state["model_client"].text2text(input_content)
                response_content = response['content'] if isinstance(response, dict) and 'content' in response else str(response)
                new_messages.append({"role": "assistant", "content": response_content})
            else:
                response = requests.post('http://10.244.31.40:6667/model', json=input_content).json()['output']
                response_content = response['content'] if isinstance(response, dict) and 'content' in response else str(response)
                new_messages.append({"role": "assistant", "content": response_content})
            
            # 提取修正后的内容
            yaml_content, python_code = self.extract_yaml_and_code(response_content)
            
            return {
                **state,
                "conversation_history": new_messages,
                "current_yaml_content": yaml_content,
                "current_python_code": python_code,
                "error_info": None
            }
            
        except Exception as e:
            return {**state, "error_info": f"调试请求失败: {str(e)}"}
    
    async def check_data_augment(self, state: WorkflowState) -> WorkflowState:
        """检查是否需要数据增强"""
        # 只有在YAML测试成功且需要数据增强时才执行
        if state["data_augment"] and state["need_data_augment"]:
            print(f"\n=== 检查数据增强: 需要执行 ===")
            return state
        else:
            print(f"\n=== 检查数据增强: 跳过 ===")
            return state
    
    async def data_augmentation(self, state: WorkflowState) -> WorkflowState:
        """数据增强"""
        print(f"\n=== 开始数据增强阶段 ===")
        
        augment_prompt = {
            "role": "user",
            "content": f"""如果生成的yaml或python代码是正向先产生输入，再通过完备的解题逻辑得到答案，那么请随机产生输入；如果是逆向先产生答案，然后再完备地验证答案正确性，最后根据正确答案产生输入，那么请随机产生输出，以此得到对应的输入。
            从而使得yaml文件能够生成更多样的题目（至少1000道不同的题目）。请使用最高效的方式保证题目答案的唯一性。按下述格式输出修改后的yaml文件。
            #### final yaml begin
            <生成的yaml文件>
            #### final yaml end
            #### final code begin
            <生成的python文件>
            #### final code end
            """
        }
        
        if state["model_client"] is not None:
            new_messages = state["conversation_history"] + [augment_prompt]
            input_content = {'messages': new_messages}
        else:
            new_messages = state["conversation_history"] + [augment_prompt]
            input_content = {'prompt': {'messages': new_messages}}
        
        try:
            if state["model_client"] is not None:
                response = await state["model_client"].text2text(input_content)
                response_content = response['content'] if isinstance(response, dict) and 'content' in response else str(response)
                new_messages.append({"role": "assistant", "content": response_content})
            else:
                response = requests.post('http://10.244.31.40:6667/model', json=input_content).json()['output']
                response_content = response['content'] if isinstance(response, dict) and 'content' in response else str(response)
                new_messages.append({"role": "assistant", "content": response_content})
            
            # 提取增强后的内容
            yaml_content, python_code = self.extract_yaml_and_code(response_content)
            
            # 标记数据增强已完成，重置错误信息
            return {
                **state,
                "conversation_history": new_messages,
                "current_yaml_content": yaml_content,
                "current_python_code": python_code,
                "need_data_augment": False,  # 数据增强只执行一次
                "error_info": None
            }
            
        except Exception as e:
            return {**state, "error_info": f"数据增强失败: {str(e)}"}
    
    async def evaluate_problem(self, state: WorkflowState) -> WorkflowState:
        """评估问题合理性"""
        if not state["model_eval_final"]:
            # 不需要评估时，直接成功并递增索引
            return {
                **state,
                "current_question_index": state["current_question_index"] + 1,
                "success_list": state["success_list"] + [state["question_names"][state["current_question_index"]]],
                "debug_times": state["debug_times"] + state["attempt_count"]
            }
        
        if not state["translator_output"]:
            return {
                **state,
                "current_question_index": state["current_question_index"] + 1,
                "error_info": "没有评估输出"
            }
        
        print(f"\n=== 开始问题评估阶段 ===")
        
        evaluation_prompt = f"""大模型生成了如下数学问题：
        {state['translator_output']}
        请评估生成的数学问题题面和答案是否清晰合理，有一定难度，与现实相符且无歧义。不需要评估答案的正确性。 
        # anlysis begin
        高质量题目: <是/否>
        原因：<原因>
        解决方案：<解决方案>
        # anlysis end
        """
        
        if state["model_client"] is not None:
            eval_conversation = [{"role": "user", "content": evaluation_prompt}]
            input_content = {'messages': eval_conversation}
        else:
            eval_conversation = [{"role": "user", "content": evaluation_prompt}]
            input_content = {'prompt': {'messages': eval_conversation}}
        
        try:
            if state["model_client"] is not None:
                response = await state["model_client"].text2text(input_content)
                response_content = response['content'] if isinstance(response, dict) and 'content' in response else str(response)
                eval_conversation.append({"role": "assistant", "content": response_content})
            else:
                response = requests.post('http://10.244.31.40:6667/model', json=input_content).json()['output']
                response_content = response['content'] if isinstance(response, dict) and 'content' in response else str(response)
                eval_conversation.append({"role": "assistant", "content": response_content})
            
            # 保存评估结果
            eval_file = os.path.join(state["current_question_folder"], "evaluation_result.txt")
            with open(eval_file, 'w', encoding='utf-8') as f:
                f.write(response_content)
            
            # 检查评估结果
            is_valid = "高质量题目: 是" in response_content
            
            if is_valid:
                # 评估通过，添加到成功列表并递增索引
                return {
                    **state,
                    "success_list": state["success_list"] + [state["question_names"][state["current_question_index"]]],
                    "current_question_index": state["current_question_index"] + 1,
                    "debug_times": state["debug_times"] + state["attempt_count"]
                }
            else:
                # 评估不通过，构建修正请求
                print(f"❌ 问题评估未通过：{response_content}")
                
                # 构建基于评估结果的修正请求
                eval_correction_prompt = {
                    "role": "user",
                    "content": f"""通过yaml和python脚本构造的造题框架生成的题目质量不高，原因和解决方案如下：
                                {response_content}
                                请按照上述解决方案逐条修改，以下述格式输出改进后的yaml和python脚本。
                                #### final yaml begin
                                <生成的yaml文件>
                                #### final yaml end
                                #### final code begin
                                <生成的python文件>
                                #### final code end
                                """
                }
                
                # 更新对话历史
                if state["model_client"] is not None:
                    new_messages = state["conversation_history"] + [eval_correction_prompt]
                else:
                    new_messages = state["conversation_history"] + [eval_correction_prompt]
                
                # 获取修正后的内容
                if state["model_client"] is not None:
                    correction_response = await state["model_client"].text2text({'messages': new_messages})
                    correction_content = correction_response['content'] if isinstance(correction_response, dict) and 'content' in correction_response else str(correction_response)
                    new_messages.append({"role": "assistant", "content": correction_content})
                else:
                    correction_response = requests.post('http://10.244.31.40:6667/model', json={'prompt': {'messages': new_messages}}).json()['output']
                    correction_content = correction_response['content'] if isinstance(correction_response, dict) and 'content' in correction_response else str(correction_response)
                    new_messages.append({"role": "assistant", "content": correction_content})
                
                # 提取修正后的YAML和代码
                yaml_content, python_code = self.extract_yaml_and_code(correction_content)
                
                return {
                    **state,
                    "conversation_history": new_messages,
                    "current_yaml_content": yaml_content,
                    "current_python_code": python_code,
                    "error_info": "评估不通过，已生成修正内容",  # 明确的错误信息
                    "attempt_count": state["attempt_count"] + 1  # 增加尝试计数
                }
                
        except Exception as e:
            return {
                **state, 
                "error_info": f"评估失败: {str(e)}",
                "current_question_index": state["current_question_index"] + 1
            }
    
    async def finalize(self, state: WorkflowState) -> WorkflowState:
        """最终处理"""
        print(f"\n{'='*60}")
        print("✅ 所有处理完成！")
        print(f"成功转换的问题: {state['success_list']}")
        print(f"总调试次数: {state['debug_times']}")
        
        # 检查是否有因为超过最大尝试次数而放弃的问题
        abandoned_questions = []
        for i, question_name in enumerate(state["question_names"]):
            if question_name not in state["success_list"]:
                abandoned_questions.append(question_name)
        
        if abandoned_questions:
            print(f"因超过最大尝试次数而放弃的问题: {abandoned_questions}")
        
        print(f"{'='*60}")
        
        # 关闭模型客户端
        if state["model_client"] is not None:
            await state["model_client"].close()
        
        return state
    
    # 工具函数 (从原代码复制)
    def extract_yaml_and_code(self, text):
        """从模型输出中提取YAML内容和Python代码"""
        # 提取YAML内容
        yaml_pattern = r'#### final yaml begin\s*(.*?)\s*#### final yaml end'
        yaml_matches = re.findall(yaml_pattern, text, re.DOTALL)
        yaml_content = None
        
        if yaml_matches:
            yaml_content = yaml_matches[-1].strip()
            yaml_code_pattern = r'```yaml\s*(.*?)\s*```'
            yaml_code_matches = re.findall(yaml_code_pattern, yaml_content, re.DOTALL)
            if yaml_code_matches:
                yaml_content = yaml_code_matches[-1].strip()
            else:
                yaml_content = yaml_content.strip()
        
        # 提取Python代码
        code_pattern = r'#### final code begin\s*(.*?)\s*#### final code end'
        code_matches = re.findall(code_pattern, text, re.DOTALL)
        python_code = None
        
        if code_matches:
            python_code = code_matches[-1].strip()
            python_code_pattern = r'```python\s*(.*?)\s*```'
            python_code_matches = re.findall(python_code_pattern, python_code, re.DOTALL)
            if python_code_matches:
                python_code = python_code_matches[-1].strip()
            else:
                python_code = python_code.strip()
        
        return yaml_content, python_code
    
    def extract_question_content(self, text, question_num):
        """提取指定问题的内容"""
        pattern = rf'# question {question_num} begin\s*(.*?)\s*# question {question_num} end'
        matches = re.findall(pattern, text, re.DOTALL)
        return matches[-1].strip() if matches else None
    
    def extract_error_info(self, error_output):
        """提取完整的错误信息"""
        if not error_output:
            return "未知错误"
        
        error_lines = error_output.strip().split('\n')
        error_info_lines = []
        
        during_handling_indices = []
        for i, line in enumerate(error_lines):
            if "During handling of the above exception, another exception occurred:" in line:
                during_handling_indices.append(i)
        
        if during_handling_indices:
            last_during_handling_index = during_handling_indices[-1]
            error_info_lines = error_lines[:last_during_handling_index]
        else:
            error_info_lines = error_lines
        
        return '\n'.join(error_info_lines).strip()
    
    def run_output_py_and_get_error(self, workspace):
        """运行output.py文件并获取其输出作为错误信息"""
        output_py_path = os.path.join(workspace, 'output.py')
        
        if not os.path.exists(output_py_path):
            return None, None
        
        try:
            result = subprocess.run(
                ['python', output_py_path],
                capture_output=True, 
                text=True, 
                timeout=30,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            
            full_output = ""
            if result.stdout:
                full_output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                full_output += f"STDERR:\n{result.stderr}\n"
            
            try:
                os.remove(output_py_path)
            except:
                pass
            
            return full_output.strip() if full_output.strip() else "output.py运行无输出", result
            
        except subprocess.TimeoutExpired:
            try:
                os.remove(output_py_path)
            except:
                pass
            return "output.py执行超时", None
        except Exception as e:
            try:
                os.remove(output_py_path)
            except:
                pass
            return f"output.py执行异常: {str(e)}", None
    
    def save_yaml_and_code(self, yaml_content, python_code, attempt_count, output_folder, each_question_name, workspace):
        """保存YAML内容和Python代码，并运行translator.py测试"""
        # 验证YAML语法
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return False, f"YAML语法错误: {str(e)}", None

        # 保存YAML文件
        yaml_filename = os.path.join(output_folder, f"temp_output.yaml")
        with open(yaml_filename, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        # 保存Python代码
        if python_code:
            with open(os.path.join(workspace, f"{each_question_name}.py"), 'w', encoding='utf-8') as f:
                f.write(python_code)
        
        try:
            # 运行translator.py
            result = subprocess.run(
                ['python', os.path.join(workspace, 'translator.py'), '-t', yaml_filename],
                capture_output=True, 
                text=True, 
                timeout=30,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            
            # 检查是否需要使用-c参数重新运行
            need_retry_with_c = (
                "toomanysolutionserror:" in result.stderr.lower() or 
                "nosolutionerror:" in result.stderr.lower() or
                "toomanysolutionserror:" in result.stdout.lower() or 
                "nosolutionerror:" in result.stdout.lower()
            )
            
            first_run_success = (
                result.returncode == 0 and 
                "answer:" in result.stdout.lower()
            )
            
            if need_retry_with_c and not first_run_success:
                try:
                    result_continue = subprocess.run(
                        ['python', os.path.join(workspace, 'translator.py'), '-t', yaml_filename, '-c'],
                        capture_output=True, 
                        text=True, 
                        timeout=30,
                        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
                    )
                    
                    continue_run_success = (
                        result_continue.returncode == 0 and 
                        "answer:" in result_continue.stdout.lower()
                    )
                    
                    # 只有在带-c参数运行成功时才替换结果
                    if continue_run_success:
                        print("使用-c参数重新运行成功！")
                        result = result_continue
                    else:
                        print("使用-c参数重新运行仍未成功，继续使用原始结果")

                except subprocess.TimeoutExpired:
                    print("使用-c参数重新运行时超时，继续使用原始结果")
                    # 不替换result，继续使用第一次运行的结果
                except Exception as e:
                    print(f"使用-c参数重新运行时出现异常: {str(e)}，继续使用原始结果")
            
            # 检查是否生成了output.py文件
            output_py_path = os.path.join(workspace, 'output.py')
            translator_success = (
                result.returncode == 0 and 
                "answer:" in result.stdout.lower()
            )
            
            if os.path.exists(output_py_path) and not translator_success:
                output_py_result, py_result = self.run_output_py_and_get_error(workspace)
                
                full_output = output_py_result
                
                success_condition = (
                    py_result and py_result.returncode == 0 and 
                    "answer:" in py_result.stdout.lower()
                )
                
                if success_condition:
                    return True, None, full_output
                else:
                    if py_result and py_result.returncode == 0 and "answer:" not in py_result.stdout.lower():
                        error_info = f"验证错误（无answer）:\n{full_output}"
                    else:
                        error_info = full_output.strip() if full_output.strip() else f"返回码: {getattr(py_result, 'returncode', '未知')}, 无错误信息"
                    
                    formatted_error = self.extract_error_info(error_info)
                    return False, formatted_error or error_info, None
            else:
                full_output = ""
                if result.stdout:
                    full_output += f"STDOUT:\n{result.stdout}\n"
                if result.stderr:
                    full_output += f"STDERR:\n{result.stderr}\n"
                
                success_condition = (
                    result.returncode == 0 and 
                    "answer:" in result.stdout.lower()
                )
                
                if success_condition:
                    return True, None, result.stdout
                else:
                    if result.returncode == 0 and "answer:" not in result.stdout.lower():
                        error_info = f"验证错误（无answer）:\n{result.stdout}"
                    else:
                        error_info = result.stderr.strip() if result.stderr.strip() else result.stdout.strip()
                        if not error_info:
                            error_info = f"返回码: {result.returncode}, 无错误信息"
                    
                    formatted_error = self.extract_error_info(error_info)
                    return False, formatted_error or error_info, None
                    
        except subprocess.TimeoutExpired:
            output_py_path = os.path.join(workspace, 'output.py')
            if os.path.exists(output_py_path):
                try:
                    os.remove(output_py_path)
                except:
                    pass
            return False, "执行超时", None
        except Exception as e:
            output_py_path = os.path.join(workspace, 'output.py')
            if os.path.exists(output_py_path):
                try:
                    os.remove(output_py_path)
                except:
                    pass
            return False, f"执行异常: {str(e)}", None


async def main_async():
    """异步主函数"""
    parser = argparse.ArgumentParser(description='数学问题转换和评估工具')
    parser.add_argument('-n', type=int, default=1, help='要生成的数学问题数量')
    parser.add_argument('-question', type=str, help='原始数学问题')
    parser.add_argument('-question_name', type=str, help='问题名称') 
    parser.add_argument('-generate_questions', action='store_true', help='是否生成相关问题')
    parser.add_argument('-model_eval_final', action='store_true', help='是否开启最终模型评估阶段')
    parser.add_argument('-data_augment', action='store_true', help='是否扩大输入范围')
    parser.add_argument("-workspace", type=str, default="/mnt/omniSSD/user_workspace/xiongkai/smt-master/SynLogic_auto_gpt5_argu_single_check3_langgraph/", help="工作空间路径")
    parser.add_argument("-output_folder", type=str, default="stage_output")
    args = parser.parse_args()
    
    # 创建输出文件夹
    os.makedirs(args.output_folder, exist_ok=True)
    
    # 初始化工作流
    workflow = MathProblemWorkflow()
    
    # 准备初始状态
    initial_state = WorkflowState(
        n=args.n,
        original_question=args.question,
        question_name=args.question_name,
        generate_questions=args.generate_questions,
        model_eval_final=args.model_eval_final,
        data_augment=args.data_augment,
        workspace=args.workspace,
        output_folder=args.output_folder,
        model_name="ep-20250822145246-jc6j8",
        
        current_stage="initialize",
        attempt_count=0,
        total_attempt=1,
        max_attempts=20,
        debug_times=0,
        need_data_augment=True,
        
        generated_questions=[],
        question_names=[],
        prepared_stages=[],
        current_question_index=0,
        current_yaml_content=None,
        current_python_code=None,
        translator_output=None,
        error_info=None,
        success_list=[],
        
        base_output_folder=args.output_folder,
        current_attempt_folder="",
        current_question_folder="",
        
        model_client=None,
        conversation_history=[]
    )
    
    # 执行工作流
    try:
        config = {"recursion_limit": 50}  # 增加递归限制
        final_state = await workflow.graph.ainvoke(initial_state, config=config)
        
        # 输出最终结果
        print(json.dumps(final_state["success_list"]))
        print(final_state["debug_times"])
        
        return len(final_state["success_list"]) > 0
        
    except Exception as e:
        print(f"工作流执行出错: {str(e)}")
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