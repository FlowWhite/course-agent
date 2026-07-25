import asyncio

from agents.exceptions import (
    MaxTurnsExceeded,
    ModelBehaviorError,
)

from app_logger import logger
from agent_runtime import (
    create_agent,
    create_session,
    run_agent_message,
)
agent = create_agent()
session = create_session("local-user")

def run_cli() -> None:
    print("课程与项目管理 Agent")
    print("输入 /new 清空当前会话。")
    print("输入 exit、quit 或 退出结束程序。\n")

    while True:
        try:
            user_input = input("你：").strip()

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit"} or user_input == "退出":
                print("程序已结束。")
                break

            if user_input == "/new":
                asyncio.run(session.clear_session())
                logger.info("用户清空会话")
                print("当前会话已清空。\n")
                continue

            logger.info("用户输入：%s", user_input)

            result = run_agent_message(
                agent,
                user_input,
                session,
            )

            logger.info("Agent 输出：%s", result.final_output)
            print(f"\nAgent：{result.final_output}\n")

        except MaxTurnsExceeded:
            logger.exception("Agent 超过最大执行轮数")
            print("\nAgent 未能在限定步骤内完成任务。\n")

        except ModelBehaviorError:
            logger.exception("模型返回了无效工具调用或无效结构")
            print("\n模型返回的数据格式不正确，请重新提问。\n")

        except KeyboardInterrupt:
            print("\n程序已结束。")
            break

        except Exception as exc:
            logger.exception("Agent 运行失败")
            print(f"\n运行失败：{type(exc).__name__}。\n")


if __name__ == "__main__":
    run_cli()
