from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SimpleField,
)
from langchain.vectorstores.azuresearch import AzureSearch

from .EnvHelper import EnvHelper
from .LLMHelper import LLMHelper


class EdsAzureSearchHelper:
    def __init__(self):
        pass

    def get_search_client(self):
        env_helper = EnvHelper()

        return SearchClient(
            endpoint=env_helper.AZURE_SEARCH_SERVICE,
            index_name=env_helper.AZURE_SEARCH_INDEX,
            credential=AzureKeyCredential(env_helper.AZURE_SEARCH_KEY)
        )

    def get_conversation_logger(self):
        llm_helper = LLMHelper()
        env_helper = EnvHelper()
        fields = [
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
            ),
            SimpleField(
                name="conversation_id",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=len(llm_helper.get_embedding_model().embed_query("Text")),
                vector_search_configuration="default",
            ),
            SearchableField(
                name="metadata",
                type=SearchFieldDataType.String,
            ),
            SimpleField(
                name="type",
                type=SearchFieldDataType.String,
                facetable=True,
                filterable=True,
            ),
            SimpleField(
                name="user_id",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="sources",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="created_at",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
            ),
            SimpleField(
                name="updated_at",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
            ),
        ]

        return AzureSearch(
            azure_search_endpoint=env_helper.AZURE_SEARCH_SERVICE,
            azure_search_key=env_helper.AZURE_SEARCH_KEY,
            index_name=env_helper.AZURE_SEARCH_CONVERSATIONS_LOG_INDEX,
            embedding_function=llm_helper.get_embedding_model().embed_query,
            fields=fields,
            user_agent="langchain chatwithyourdata-sa",
        )
