# ============================================================================
# audit_index.py —— 入库前的「三列体检报告」
#
# 【这张脚本要干什么 · 一句话】
#   给 chunks / metas / vectors 三列做对齐体检，把「看不见的错位」变成一条条
#   人话问题，最后给一句「可以入库 / 禁止入库」的结论。
#
# 【为什么 build_index.py 里那句长度校验还不够】
#   那句 if 只能挡「数量不对」；数量对得上、但某一格是空向量 / 出处卡缺字段，
#   Chroma 照样收下，日志照样全绿 —— 又是本讲说的「最阴的静默错误」。
#   长度是「表有几行」，体检还要查「每行格子里有没有东西」。
#
# 【本函数最容易写错的一处】用 range(max(...)) 而**不是** zip 遍历：
#   zip 遇到三列不等会静默截断到最短列，多出来的块根本不被检查 ——
#   体检工具自己就犯了本讲刚讲的那个错。
#
# 【职责边界】本函数只「报告」，不 raise、不拦路；真正拦路的是 build_index.py 里
#   那句 `if not (...): raise RuntimeError(...)`。分开后这工具既能单独跑，
#   以后也能接进主链路打印体检单，不会一发现小毛病就把脚本打断。
# ============================================================================


def audit_index(chunks, metas, vectors):
    # ─────────────────────────────────────────────────────────────────────
    # 【目标】入库前把三列对齐情况写成一份人话报告。
    # 【输入】chunks = 原文块列表；metas = 出处卡字典列表；vectors = 向量列表
    # 【输出】report 字符串（多行，用 "\n".join 拼），最后一行是结论
    # 【检查四项】① 三列长度 ② 每块原文是否为空 ③ 出处卡是否缺字段
    #            ④ 向量是否为空 / 维度是否一致
    # 【为什么逐块查】长度一致 ≠ 内容对齐；三列都是 3 条，也可能第 2 张卡缺 page。
    # ─────────────────────────────────────────────────────────────────────

    n_chunk = len(chunks)
    # 做什么：取出原文列的条数。
    # 为什么：后面反复要用，先存变量比每行写一次 len(chunks) 清楚，也少算几次。
    n_meta = len(metas)
    # 做什么：取出出处卡列的条数。
    n_vec = len(vectors)
    # 做什么：取出向量列的条数。

    problems = []
    # 做什么：空列表，装一条条人话问题，最后统一拼成报告。
    # 为什么：报告要先收集再输出，不能边查边 print —— 那样以后接进主链路就没法复用。

    has_error = False
    # 做什么：一个开关，只要发现任何问题就置 True。
    # 为什么：比「最后扫一遍报告文字里有没有 ❌」稳得多，不会被报告内容误伤。

    dims = set()
    # 做什么：空集合，用来记「见过哪些向量维度」。
    # 为什么：set 会自动去重，最后只要 len(dims) > 1 就说明维度不统一；
    #         用列表还得自己写 if x not in dims。

    if n_chunk == 0:
        # 做什么：一块原文都没有的情况单独点名。
        # 为什么：三列全空时「长度一致 ✅」会成立，但建出空库毫无意义 ——
        #         呼应 build_index.py 里的 `if not chunks: raise`。

        problems.append("❌ 一块原文都没有：别建空库，先检查 data/ 目录")
        has_error = True

    if not (n_chunk == n_meta == n_vec):
        # 做什么：验票 —— 三个长度必须一模一样。
        # 为什么：col.add 是「按位置配对」的四列表格，少一列后面全体往前串一位，
        #         原文配到别人的向量、别人的页码，又是一次不报错的静默错位。
        # 语法：a == b == c 是链式比较，等价 a==b 且 b==c；前面加 not = 只要不全相等就进来。

        problems.append(
            f"❌ 三列长度不一致：原文 {n_chunk} / 出处卡 {n_meta} / 向量 {n_vec}"
            " —— 按位置配对必然串位"
        )
        # 做什么：把三列的实际条数写进报告，一眼看出是哪列少了。
        # 为什么：只说「不一致」还得自己回去数，体检单要给出可直接行动的信息。
        has_error = True
    elif n_chunk > 0:
        problems.append(f"✅ 三列长度一致：各 {n_chunk} 条")
        # 做什么：没问题也写一行。
        # 为什么：报告要能自证「查过了」，不能只在不通过时才出声。
        # ⚠️ 为什么加 `n_chunk > 0`：三列全空时长度确实相等，会同时打出
        #    「✅ 各 0 条」和上面「❌ 别建空库」，一句绿一句红自相矛盾 ——
        #    实跑用例 ⑤ 抓到的坑。体检报告自己不能让人不知道该信哪句。

    count = max(n_chunk, n_meta, n_vec)
    # 做什么：用「最长的一列」定遍历次数。
    # 为什么：三列不等时，多出来的那些块也必须被逐条点名，不能被悄悄跳过。

    for i in range(count):
        # 做什么：按最长列的下标，一行一行查。
        # ⚠️ 为什么绝不能用 zip：zip(chunks, metas, vectors) 遇到长度不等会
        #    **静默截断到最短列**，多出来的块根本不进循环 —— 体检工具自己
        #    就犯了本讲刚讲的那个「最阴的静默错误」，查完还报「一切正常」。

        chunk = chunks[i] if i < n_chunk else None
        # 做什么：这一列有第 i 条就取出来，没有就给 None。
        # 为什么：不写 `i < n_chunk` 的判断，长度不等时直接 chunks[i] 会抛 IndexError，
        #          体检工具反而先崩了（查错的工具自己不能出错）。
        # 语法：`A if 条件 else B` 是条件表达式（三元），满足取 A 否则取 B。

        meta = metas[i] if i < n_meta else None
        # 做什么：出处卡同样按下标取，缺就给 None。
        vec = vectors[i] if i < n_vec else None
        # 做什么：向量同样按下标取，缺就给 None。

        if chunk is None or not str(chunk).strip():
            # 做什么：判这一格原文是不是「没有 / 空白」。
            # 为什么：空白块进库会占据一个 id，检索时命中一堆没内容的东西。
            # 语法：str(...) 先把非字符串也转成字符串；.strip() 去掉首尾空白；
            #       空字符串在 Python 里算「假」，所以 not "" 为真。
            problems.append(f"  · 第 {i} 块：原文为空 / 这一列缺这条")
            has_error = True

        if meta is None:
            # 做什么：整张出处卡都没有。
            problems.append(f"  · 第 {i} 块：缺整张出处卡片（以后没法溯源）")
            has_error = True
        elif not isinstance(meta, dict):
            # 做什么：卡片不是字典（可能被误塞了字符串、列表）。
            # 为什么：不是字典就没有 .get()，下面那行会 AttributeError；
            #         isinstance(对象, 类型) 就是问「你是不是这个类型」。
            problems.append(f"  · 第 {i} 块：出处卡不是字典，是 {type(meta).__name__}")
            # 做什么：type(...).__name__ 只取类型名字（如 str、list），报告里更好读。
            has_error = True
        else:
            missing = [k for k in ("source", "page") if meta.get(k) in (None, "")]
            # 做什么：列表推导式，只留下「没填」的字段名。
            # 为什么：卡片可能整张在、但少写了 page，这种「数量对内容缺」最容易漏。
            # 语法：dict.get(k) 取不到时返回 None，不会像 dict[k] 那样抛 KeyError。
            # ⚠️ 用 `in (None, "")` 而不是 `not meta.get(k)`：后者会把合法的
            #    0 / False 也误判成缺失（将来 page 若允许 0 就会冤枉它）。
            if missing:
                problems.append(f"  · 第 {i} 块：出处卡缺 {'、'.join(missing)}")
                # 做什么：把缺的字段名用顿号拼成一句，例如「source、page」。
                # 为什么：只说「卡有问题」还得自己打开看，体检单要点名到字段。
                has_error = True

        if vec is None:
            # 做什么：这一列根本没给第 i 条向量。
            problems.append(f"  · 第 {i} 块：没有向量（这一列缺这条）")
            has_error = True
        elif not isinstance(vec, (list, tuple)) or len(vec) == 0:
            # 做什么：判向量是不是「不是数字列表 / 空列表 []」。
            # 为什么：**必须先判类型再 len()** —— 对 None 或数字直接 len 会 TypeError；
            #         Python 的 or 是短路的，前面成立就不会去算后面的 len。
            #         空向量进库等于这块没有坐标，检索永远命中不了它。
            problems.append(f"  · 第 {i} 块：空向量 / 不是数字列表")
            has_error = True
        else:
            dims.add(len(vec))
            # 做什么：把这条向量的维度记进集合（1024 就是 1024，重复的不记）。
            # 为什么：如果一批 1024、一批 768，说明混了模型或被截断，
            #         数量看着全对，但检索结果不可信 —— 又是个静默错误。

    if len(dims) > 1:
        # 做什么：集合里出现了不止一种维度。
        problems.append(f"❌ 向量维度不一致：{sorted(dims)} —— 混了模型或被截断，检索不可信")
        # 做什么：sorted() 排个序再打印，输出稳定好读。
        has_error = True

    if has_error:
        # 做什么：根据开关给结论，而不是靠翻报告文字猜。
        problems.append("❌ 结论：禁止入库 —— 修好上面的问题再重建索引")
    else:
        problems.append("✅ 结论：体检通过，可以入库")

    return "\n".join(problems)
    # 做什么：把一条条问题用换行拼成一整份报告。
    # 为什么：返回字符串而不是直接 print，调用方想打印、写日志、塞进断言都行；
    #         分隔符用 "\n" 是「记录级纵向分条」（第 8 课两个 join 的套路）。


if __name__ == "__main__":
    # 做什么：只有「直接运行本文件」才跑下面 5 组自测；被别的文件 import 时不自动打印。
    # 为什么：以后 build_index.py 想 import 这个体检函数，不该顺带输出一堆测试文字。

    # 造 3 块教学假数据；只体检结构，不需要真的调 API
    good_chunks = ["甲 现金流320亿", "乙 营收增长14.3%", "丙 风险提示"]
    # 做什么：3 条原文块。
    good_metas = [
        {"source": "示例研报.txt", "page": 1},
        {"source": "示例研报.txt", "page": 2},
        {"source": "示例研报.txt", "page": 3},
    ]
    # 做什么：3 张出处卡，每张都带 source 和 page。
    good_vectors = [[0.1] * 1024 for _ in range(3)]
    # 做什么：列表推导造 3 条 1024 维假向量（[0.1] * 1024 把 0.1 重复 1024 次）。
    # 为什么：用假向量就能测结构，不用花 API 额度，也不用等网络。
    # 语法：`for _ in range(3)` 里的下划线是惯例写法，表示「这个变量我不用」。

    cases = [
        ("① 全部正常", good_chunks, good_metas, good_vectors),
        ("② 向量少一条（长度不等）", good_chunks, good_metas, good_vectors[:2]),
        ("③ 第 2 块出处卡缺 page", good_chunks,
         [good_metas[0], {"source": "示例研报.txt"}, good_metas[2]], good_vectors),
        ("④ 第 3 块是空向量", good_chunks, good_metas,
         [good_vectors[0], good_vectors[1], []]),
        ("⑤ 三列全空", [], [], []),
    ]
    # 做什么：把 5 组用例装进列表，每组是「标题 + 三列数据」。
    # 为什么：循环跑比复制 5 遍调用省事，也方便以后加新用例。

    for title, c, m, v in cases:
        # 做什么：一次拆包取出标题和三列数据。
        print(f"\n=== {title} ===")
        # 做什么：打印分组标题；"\n" 先空一行更好读。
        print(audit_index(c, m, v))
        # 做什么：打印这份体检报告（函数返回的是字符串，不是自己 print）。
