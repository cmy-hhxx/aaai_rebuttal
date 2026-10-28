

def simulate_engineer_teams(days_alone,work_days,off_days):
    # 工程总量为 1
    total_work = 1.0

    # 计算各自每天的工作效率（基于实际工作天数）
    act_work_days = []
    for i in range(len(days_alone)):
        act_work_days.append((days_alone[i]//(work_days[i]+off_days[i]))*work_days[i]+min(work_days[i],days_alone[i]%(work_days[i]+off_days[i])))

    # work_days_a = (days_alone_a // 6) * 5 + min(days_alone_a % 6, 5)
    # work_days_b = (days_alone_b // 8) * 6 + min(days_alone_b % 8, 6)

    # 计算每天的效率
    efficiencys = [1/item for item in act_work_days]

    # efficiency_a = 1 / work_days_a
    # efficiency_b = 1 / work_days_b

    # print(f"每天效率: {efficiencys}")

    # print(f"甲每天效率: {efficiency_a:.4f}")
    # print(f"乙每天效率: {efficiency_b:.4f}")

    # 模拟每一天
    day = 0
    completed_work = 0.0

    while completed_work < total_work:
        day += 1

        # 判断是否为工作日

        work_or_not_list = []

        for i in range(len(work_days)):
            if (day-1) % (work_days[i]+off_days[i]) < work_days[i]:
                work_or_not_list.append(True)
            else:
                work_or_not_list.append(False)

        # # 判断是否是甲的工作日
        # if (day - 1) % 6 < 5:  # 第1天开始计数，所以减1
        #     a_working = True
        # else:
        #     a_working = False

        # # 判断是否是乙的工作日
        # if (day - 1) % 8 < 6:
        #     b_working = True
        # else:
        #     b_working = False

        # 累加当天的工作量
        for i, work_or_not in enumerate(work_or_not_list):
            if work_or_not:
                completed_work += efficiencys[i]
        # print(completed_work)
        # if a_working:
        #     completed_work += efficiency_a
        # if b_working:
        #     completed_work += efficiency_b

        # 可选：打印每日进度
        # print(f"第{day}天: 甲工作={a_working}, 乙工作={b_working}, 累计工作量={completed_work:.4f}")

    return day


if __name__ == '__main__':

    # 单独完成所需天数
    # days_alone_a = 62
    # days_alone_b = 51

    days_alone = [70,47,72,69,51]
    work_days = [5,7,7,4,4]
    off_days = [1,2,1,1,1]

    # 运行模拟
    required_days = simulate_engineer_teams(days_alone,work_days,off_days)
    print(f"\n✅ 两队合作共需 {required_days} 天完成工程")