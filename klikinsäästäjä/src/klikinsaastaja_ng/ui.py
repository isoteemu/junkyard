import logging
import os
from dotenv import load_dotenv
import gradio as gr
from klikinsaastaja_ng.main import get_prompt, PromptFiles, user_prompt_file
from klikinsaastaja_ng.settings import settings
from klikinsaastaja_ng.utils import parse_bot_response

os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'false')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', 'true')
logger = logging.getLogger(__name__)

load_dotenv()


def save_user_prompt(prompt: str):
    prompt_file = user_prompt_file(PromptFiles.INTEREST_GROUP)
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Saving prompt to %r", prompt_file)
    prompt_file.write_text(prompt)
    logger.info("Prompt saved to %r", prompt_file)
    yield gr.Info(f"Prompt saved to {prompt_file}")


def _hf_download_model(model: str, token: str, progress=gr.Progress(track_tqdm=True)):
    """
    Download model from Hugging Face Hub
    """
    from huggingface_hub import snapshot_download
    logger.debug("Downloading model %r", model)

    # Add repo to the model name
    if "/" not in model:
        model = f"sentence-transformers/{model}"

    try:
        model_path = snapshot_download(model, token=token or None) 
        logger.info("Model %r downloaded to %r", model, model_path)
        yield model
    except Exception as e:
        logger.exception("Failed to download model %r", model, exc_info=e, extra={"model": model, "token": token})
        yield gr.Info(f"Failed to download model {model}: {e}")


def save_settings(*args, **kwargs):
    """
    Save settings
    """
    logger.debug("Saving settings")
    print(args, kwargs)
    yield gr.Info("Settings saved")

def ui_page_settings():
    """
    Settings page.
    """

    with gr.Tab("Settings") as settings_tab:

        with gr.Group():
            # gr.Markdown("Select the embedding function to use for the analysis. Embeddings are a numerical representation of text that can be used to measure the relatedness between two pieces of text.")
            embedding_function = gr.Radio(
                [
                    ("Sentence Transformers on Hugging Face (local)", "HuggingFaceEmbeddings"),
                    ("GPT4All (local)", "GPT4AllEmbeddings"),
                    ("OpenAI (remote)", "OpenAIEmbeddings"),
                    ("Fake Embeddings (for testing)", "FakeEmbeddings"),
                ],
                label="Embedding function",
                value=settings.embedding_function,
            )

            with gr.Group(visible=settings.embedding_function == "HuggingFaceEmbeddings") as huggingface_group:
                hf_token = gr.Textbox(settings.hf_token, lines=1, label="Hugging Face Token (Optional)")
                with gr.Row():
                    hf_model = gr.Dropdown(
                        [
                            "sentence-transformers/all-MiniLM-L6-v2",
                            "sentence-transformers/all-MiniLM-L12-v2",
                            "jinaai/jina-embeddings-v2-small-en"
                        ],
                        label="Hugging Face Model",
                        value=settings.hugginface_embedding_model,
                        allow_custom_value=True,
                    )

                    hf_download = gr.Button("Download Model", size="sm")
                    hf_download.click(_hf_download_model, [hf_model, hf_token], outputs=[hf_model])

            with gr.Group(visible=settings.embedding_function == "OpenAIEmbeddings") as openai_group:
                openai_api_key = gr.Textbox(
                    settings.openai_api_key,
                    lines=1,
                    label="OpenAI API Key",
                    info="OpenAI is a remote service that requires an API key. You can get one from https://platform.openai.com/account/api-keys",
                )
                openai_model = gr.Dropdown(
                    ["text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"],
                    label="OpenAI Model",
                    value=settings.openai_embedding_model,
                )

            def on_embedding_function_changed(embedding_function: str):
                print("Embedding function changed to %r", embedding_function)
                return {
                    huggingface_group: gr.Group(visible=embedding_function == "HuggingFaceEmbeddings"),
                    openai_group: gr.Group(visible=embedding_function == "OpenAIEmbeddings"),
                }
            embedding_function.change(on_embedding_function_changed, [embedding_function], outputs=[huggingface_group, openai_group])

        with gr.Group():
            edgegpt_bing_cookie__U = gr.Textbox(
                settings.edgegpt_bing_cookie__U,
                lines=1,
                label="Bing `_U` cookie",
                info=settings.model_fields["edgegpt_bing_cookie__U"].description,
            )

        bts_save = gr.Button("Save", size="sm")
        # bts_save.click(save_settings, [embedding_function, hf_token, hf_model, openai_api_key, openai_model, edgegpt_bing_cookie__U])
    return settings_tab


def analyze_article(url: str, prompt: str, progress=gr.Progress()):
    """
    Analyze the article
    """
    logger.debug("Analyzing article %r", url)

    from .outlet import build
    from .bot import invoke

    if not url:
        raise gr.Error("URL is required")

    yield [f"Fetching article {url!r}", None]
    formatterd_prompt, webpage = build(url, prompt)
    yield [f"Article: {webpage}", None]

    result = invoke(formatterd_prompt, webpage)
    logger.debug("Bot response: %r", result)
    response = parse_bot_response(result)

    data_rows = [d.values() for d in response]

    yield [
        result,
        data_rows,
    ]
    return


def analyze_with_rag(*args, **kwargs):
    for i in args:
        print("ROW", type(i))


def gradio_ui():
    with gr.Blocks(title="Klikinsäästäjä NG") as app:
        with gr.Tab("Vested Interest Groups"):
            with gr.Group():
                with gr.Accordion('Prompt', open=False):
                    party_prompt = gr.Code(get_prompt(PromptFiles.INTEREST_GROUP), lines=7, label="Instructions for detecting interest groups", language="markdown")
                    save = gr.Button("Save", size="sm")
                    save.click(save_user_prompt, party_prompt)
                with gr.Row():

                    url = gr.Textbox("", label="URL", lines=1, placeholder="https://example.com")
                    analyze_btn = gr.Button("Analyze")

                with gr.Accordion('Response', open=False):
                    analyze_result_output = gr.Textbox("", label="Raw response", lines=7)

                with gr.Row():
                    analyze_result = gr.Dataframe(
                        headers=["lang", "group", "wikipedia query", "reasoning", "rag query"],
                    )

            analyze_btn.click(analyze_article, [url, party_prompt], outputs=[analyze_result_output, analyze_result])

        with gr.Tab("News analyzer"):
            with gr.Accordion('Prompt', open=False), gr.Group():
                party_prompt = gr.Code(get_prompt(PromptFiles.ARTICLE_TITLE), lines=7, label="Instructions for generating a less sensational title", language="markdown")
                save = gr.Button("Save", size="sm")
                #save.click(save_user_prompt, party_prompt)

            with gr.Group(), gr.Row():
                news_url = gr.Textbox("", label="News URL", placeholder="http://www.example.com/neeeews")
                analyze_news_btn = gr.Button("Suggest a new title")

            with gr.Group():
                suggested_title = gr.Textbox("", label="Suggested title")
                analyze_news_title_result = gr.Dataframe(
                    headers=["title", "reasoning", "clickbaitiness score"],
                )

            analyze_news_btn.click(analyze_with_rag, [analyze_result])

        settings = ui_page_settings()

    return app

if __name__ == "__main__":
    from .utils import setup_logging
    setup_logging(logger)

    app = gradio_ui()
    app.queue()
    app.launch()
