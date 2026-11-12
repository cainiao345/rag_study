import os
# 导入 os：Python 自带的「系统工具箱」，这里用来读环境变量

from dotenv import load_dotenv
# 从 python-dotenv 库导入 load_dotenv：把 .env 里的「键=值」搬进环境变量
# 第一次用要先装依赖：pip install -r requirements.txt

REQUIRED = [
    # 常量列表：4 个「必须填好」的变量名
    # 全大写是 Python 的「常量」约定，表示这个列表配置好就不该在程序里改
    "DEEPSEEK_API_KEY",      # 生成答案用的 key（DeepSeek）
    "SILICONFLOW_API_KEY",   # 向量化用的 key（硅基流动），和上面是两把不同的钥匙
    "EMBED_BASE_URL",        # 向量化服务地址：https://api.siliconflow.cn/v1
    "EMBED_MODEL",           # 向量模型名：BAAI/bge-m3
]
# 注意：DEEPSEEK_BASE_URL 不在这里，因为代码里给它写了默认值，缺了也能跑


def check_env():
    # 定义函数：配置齐备返回 True；缺了就抛 RuntimeError 让程序立刻停下
    # 这是「防呆」：与其等 API 报一个含糊的 401，不如启动时就说清缺什么

    load_dotenv()
    # 读当前目录下的 .env；不调这一句，os.getenv 会全部拿到空值

    missing = []
    # 空列表：装「没填好」的变量**名**（只装名字，绝不装值，防止密钥进日志）

    for name in REQUIRED:
        # 一个一个检查上面列出的 4 个变量

        value = os.getenv(name, "").strip()
        # os.getenv(名, 默认值)：按名字取值，没配就返回第 2 个参数 ""（空字符串）
        # .strip()：去掉首尾空格，防止只填了一堆空格也被误当成「配好了」
        # 这样 value 一定是字符串，下面才能安全地用 startswith

        if not value or value.startswith("your_"):
            # not value：空字符串在 Python 里算「假」→ 压根没配
            # startswith("your_")：还是 .env.example 里的占位样例，也算没填
            # 两种情况都记进 missing
            missing.append(name)
            # 只追加变量名，绝不追加 value —— 这是本题的安全红线

    if missing:
        # 非空列表算「真」→ 确实有变量没配好
        raise RuntimeError("缺少环境变量：" + "、".join(missing))
        # raise：主动抛异常，程序到此停止，不会带着残缺配置继续跑
        # "、".join(missing)：用顿号把变量名横向拼成一句
        # 错误信息里只有变量名，没有任何密钥值

    print("配置检查通过 ✅ EMBED_MODEL =", os.getenv("EMBED_MODEL"))
    # 模型名不是秘密，可以打印；两把 key 一个都不打印
    # 打印这行也是给使用者一个「配置确实读到了」的确认

    return True
    # 返回 True：方便别的文件写 if check_env(): 再继续启动


if __name__ == "__main__":
    # 只有「直接运行本文件」时才执行下面这行
    # 被别的文件 import 时不会自动跑，避免一导入就抛错
    check_env()
