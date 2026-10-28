#!/bin/bash

INPUT_FILE="/mnt/omniSSD/user_workspace/xiongkai/smt-master/SynLogic_auto_gpt5_argu_single_check3_langgraph/SynLogic_data.jsonl"
OUTPUT_BASE_FOLDER="results_eval_data"
LOG_FILE="processing_results.log"

mkdir -p "$OUTPUT_BASE_FOLDER"

total_success_list=()
total_processed=0
debug_times_total=0
total_questions=$(grep -cve '^\s*$' "$INPUT_FILE")

echo "总问题数: $total_questions"
echo "开始处理..."

while IFS= read -r line; do
    [[ -z "$line" ]] && continue

    id=$(jq -r '.id' <<< "$line")
    question=$(jq -r '.question' <<< "$line")
    answer=$(jq -r '.answer' <<< "$line")
    output_folder="$OUTPUT_BASE_FOLDER/$id"

    # 将answer拼接到question后面
    full_question="${question} answer: ${answer}"

    echo "处理 ID: $id"
    echo "执行 Python 脚本..."

    # 临时文件
    temp_file=$(mktemp)

    # 运行 Python 并实时输出
    python -u run_support_code_langgraph.py \
        -question "$full_question" \
        -question_name "$id" \
        -output_folder "$output_folder" \
        -data_augment \
        -model_eval_final \
        2>&1 | tee "$temp_file"

    # 取倒数第 2 行（Success_list）
    success_line=$(tail -n 2 "$temp_file" | head -n 1)
    # 取倒数第 1 行（Debug_times）
    debug_line=$(tail -n 1 "$temp_file")

    echo "Success_list 行: $success_line"
    echo "Debug_times 行:  $debug_line"

    #### ------ 解析 Success_list ------ ####
    if jq -e 'type=="array"' <<< "$success_line" >/dev/null 2>&1; then
        while IFS= read -r success_id; do
            [[ -n "$success_id" && "$success_id" != "null" ]] && total_success_list+=("$success_id")
        done < <(jq -r '.[]' <<< "$success_line")
    fi

    #### ------ 解析 Debug_times ------ ####
    # 判断是否为数字
    if [[ "$debug_line" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
        debug_times_total=$(awk "BEGIN {print $debug_times_total + $debug_line}")
    else
        echo "警告：Debug_times 不是数字: $debug_line"
    fi

    rm -f "$temp_file"

    ((total_processed++))
    echo "进度: $total_processed/$total_questions"
    echo "----------------------------------------"

done < "$INPUT_FILE"

#### ------ 统计与输出 ------ ####

success_count=${#total_success_list[@]}
success_rate=$(awk "BEGIN {printf \"%.2f\", $success_count / $total_questions * 100}")
avg_debug_times=$(awk "BEGIN {printf \"%.4f\", $debug_times_total / $success_count}")

# 输出到控制台和日志文件
{
echo "=== 处理完成 ==="
echo "总问题数: $total_questions"
echo "成功数量: $success_count"
echo "成功率: $success_rate%"
echo "平均 Debug_times: $avg_debug_times"
echo "成功 ID 列表:"
for id in "${total_success_list[@]}"; do
    echo "- $id"
done
} | tee "$LOG_FILE"

echo "详细结果已保存到: $LOG_FILE"