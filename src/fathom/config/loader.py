import os

# 定义配置文件的路径
import pathlib
import tomllib
from typing import Any, Dict

from dotenv import load_dotenv

CONFIG_PATH = pathlib.Path(__file__).parent / "config.toml"

load_dotenv()


class ConfigLoader:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """Load TOML configuration file and handle override of environment variables"""
        if not os.path.exists(CONFIG_PATH):
            raise FileNotFoundError(
                f"Configuration file {CONFIG_PATH} has not been found."
            )

        with open(CONFIG_PATH, "rb") as f:
            self._config = tomllib.load(f)

        # Security Best Practices: Reading API Keys from Environment Variables
        # Inject `env` into config dict
        self._config["llm"]["api_key"] = os.getenv("API_KEY")
        self._config["llm"]["base_url"] = os.getenv("BASE_URL")
        self._config["search"]["api_key"] = os.getenv("TAVILY_API_KEY")

    @property
    def config(self):
        return self._config

    # 提供一些快捷访问属性，方便在 Graph Node 中使用
    @property
    def max_depth(self):
        return self._config["research"]["max_depth"]

    @property
    def max_sub_questions(self):
        return self._config["research"]["max_sub_questions"]

    @property
    def report_model(self):
        return self._config["llm"]["report_model_name"]

    @property
    def summary_model(self):
        return self._config["llm"].get("summary_model_name", self.report_model)

    @property
    def clarify_model(self):
        return self._config["llm"].get("clarify_model_name", self.report_model)

    @property
    def research_model(self):
        return self._config["llm"].get("research_model_name", self.report_model)


# --- 使用示例 ---
if __name__ == "__main__":
    # 实例化
    settings = ConfigLoader()

    # 打印测试
    print(f"当前项目: {settings.config['project']['name']}")
    print(f"使用模型: {settings.report_model}")
    print(f"研究深度: {settings.max_depth}")

    # 在 LangGraph 的 Node 中使用：
    # if state["iteration"] >= settings.max_depth:
    #     return "finalize"
