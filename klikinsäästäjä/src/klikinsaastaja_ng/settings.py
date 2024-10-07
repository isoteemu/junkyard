from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):

    embedding_function: str = Field(default="HuggingFaceEmbeddings")

    hf_token: str = Field(default="", env="HF_TOKEN")
    hugginface_embedding_model: str = Field(default="all-MiniLM-L6-v2")

    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_embedding_model: str = Field(default="text-embedding-3-small")

    edgegpt_bing_cookie__U: str | None = Field(
        default="",
        env="BING_U",
        description="The `_U` cookie from bing.com. Bing cookie is required for the EdgeGPT chatbot to work. You can get it from the browser's devtools.",
    )


settings = Settings()
