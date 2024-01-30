# ! pip install ./whl/azure_search_documents-11.4.0b12-py3-none-any.whl --quiet
# ! pip install openai azure-storage-blob python-dotenv --quiet
# Import required libraries
import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes._generated.models import IndexerExecutionEnvironment
from azure.search.documents.indexes.models import (
    AzureOpenAIEmbeddingSkill,
    AzureOpenAIParameters,
    AzureOpenAIVectorizer,
    ExhaustiveKnnParameters,
    ExhaustiveKnnVectorSearchAlgorithmConfiguration,
    FieldMapping,
    HnswParameters,
    HnswVectorSearchAlgorithmConfiguration,
    IndexProjectionMode,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    PrioritizedFields,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjections,
    SearchIndexerIndexProjectionsParameters,
    SearchIndexerSkillset,
    SemanticConfiguration,
    SemanticField,
    SemanticSettings,
    SplitSkill,
    VectorSearch,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
    IndexingParameters,
    IndexingParametersConfiguration, SearchableField,
)
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

from backend.utilities.helpers.EnvHelper import EnvHelper

env_helper = EnvHelper()

# Configure environment variables
load_dotenv()
service_endpoint = env_helper.AZURE_SEARCH_SERVICE
index_name = env_helper.AZURE_SEARCH_INDEX
key = env_helper.AZURE_SEARCH_KEY
credential = AzureKeyCredential(key)

model: str = "text-embedding-ada-002"
blob_connection_string = os.getenv("BLOB_CONNECTION_STRING")
container_name = os.getenv("BLOB_CONTAINER_NAME")

client = SearchIndexerClient(endpoint=service_endpoint, credential=credential)


def connect_to_blog():
    """
    Connect to Blob Storage
    :return:
    """
    blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    blobs = container_client.list_blobs()

    first_blob = next(blobs)
    blob_url = container_client.get_blob_client(first_blob).url
    print(f"URL of the first blob: {blob_url}")


def create_data_source():
    """
    Create Data Source
    :return:
    """
    container = SearchIndexerDataContainer(name=container_name)
    data_source_connection = SearchIndexerDataSourceConnection(
        name=f"{index_name}-blob",
        type="azureblob",
        connection_string=blob_connection_string,
        container=container
    )
    data_source = client.create_or_update_data_source_connection(data_source_connection)

    print(f"Data source '{data_source.name}' created or updated")

    return data_source


def create_search_index():
    """
    Create a search index
    :return:
    """
    index_client = SearchIndexClient(endpoint=service_endpoint, credential=credential)
    fields = [
        SearchField(name="parent_id", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),
        SearchField(name="title", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True,
                    retrievable=True),
        SearchField(name="id", type=SearchFieldDataType.String, key=True, sortable=True, filterable=True,
                    facetable=True, analyzer_name="keyword", retrievable=True),
        # SearchField(name="content", type=SearchFieldDataType.String, sortable=False, filterable=False, facetable=False),
        SearchableField(name="content", type=SearchFieldDataType.String, sortable=False, filterable=False,
                        facetable=False, retrievable=True),
        SearchField(name="content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=1536, vector_search_profile="myHnswProfile", retrievable=True),
        SearchField(name="metadata", type=SearchFieldDataType.String, sortable=False, filterable=False, facetable=False,
                    retrievable=True, searchable=True),
        SearchField(name="source", type=SearchFieldDataType.String, sortable=False, filterable=True, facetable=False,
                    retrievable=True, searchable=True),
        SearchField(name="chunk", type=SearchFieldDataType.String, sortable=False, filterable=True, facetable=False,
                    retrievable=True, searchable=False),
        SearchField(name="offset", type=SearchFieldDataType.String, sortable=False, filterable=True, facetable=False,
                    retrievable=True, searchable=False),
    ]

    # Configure the vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswVectorSearchAlgorithmConfiguration(
                name="myHnsw",
                kind=VectorSearchAlgorithmKind.HNSW,
                parameters=HnswParameters(
                    m=4,
                    ef_construction=400,
                    ef_search=500,
                    metric=VectorSearchAlgorithmMetric.COSINE,
                ),
            ),
            ExhaustiveKnnVectorSearchAlgorithmConfiguration(
                name="myExhaustiveKnn",
                kind=VectorSearchAlgorithmKind.EXHAUSTIVE_KNN,
                parameters=ExhaustiveKnnParameters(
                    metric=VectorSearchAlgorithmMetric.COSINE,
                ),
            ),
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm="myHnsw",
                vectorizer="myOpenAI",
            ),
            VectorSearchProfile(
                name="myExhaustiveKnnProfile",
                algorithm="myExhaustiveKnn",
                vectorizer="myOpenAI",
            ),
        ],
        vectorizers=[
            AzureOpenAIVectorizer(
                name="myOpenAI",
                kind="azureOpenAI",
                azure_open_ai_parameters=AzureOpenAIParameters(
                    resource_uri=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    deployment_id=model,
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                ),
            ),
        ],
    )

    semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=PrioritizedFields(
            prioritized_content_fields=[SemanticField(field_name="content")]
        ),
    )

    # Create the semantic settings with the configuration
    semantic_settings = SemanticSettings(configurations=[semantic_config])

    # Create the search index with the semantic settings
    index = SearchIndex(name=index_name,
                        fields=fields,
                        vector_search=vector_search,
                        semantic_settings=semantic_settings)
    result = index_client.create_or_update_index(index)
    print(f"{result.name} created")


def create_skillset():
    # Create a skillset
    skillset_name = f"{index_name}-skillset"

    split_skill = SplitSkill(
        description="Split skill to chunk documents",
        text_split_mode="pages",
        context="/document",
        maximum_page_length=2048,
        page_overlap_length=20,
        inputs=[
            InputFieldMappingEntry(name="text", source="/document/content"),
        ],
        outputs=[
            OutputFieldMappingEntry(name="textItems", target_name="pages")
        ],
    )

    embedding_skill = AzureOpenAIEmbeddingSkill(
        description="Skill to generate embeddings via Azure OpenAI",
        context="/document/pages/*",
        resource_uri=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_id=model,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        inputs=[
            InputFieldMappingEntry(name="text", source="/document/pages/*"),
        ],
        outputs=[
            OutputFieldMappingEntry(name="embedding", target_name="content_vector")
        ],
    )

    index_projections = SearchIndexerIndexProjections(
        selectors=[
            SearchIndexerIndexProjectionSelector(
                target_index_name=index_name,
                parent_key_field_name="parent_id",
                source_context="/document/pages/*",
                mappings=[
                    InputFieldMappingEntry(name="content", source="/document/pages/*"),
                    InputFieldMappingEntry(name="content_vector", source="/document/pages/*/content_vector"),
                    InputFieldMappingEntry(name="title", source="/document/metadata_storage_name"),
                ],
            ),
        ],
        parameters=SearchIndexerIndexProjectionsParameters(
            projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
        ),
    )

    skillset = SearchIndexerSkillset(
        name=skillset_name,
        description="Skillset to chunk documents and generating embeddings",
        skills=[split_skill, embedding_skill],
        index_projections=index_projections,
    )

    client.create_or_update_skillset(skillset)
    print(f"{skillset.name} created")


def create_indexer(is_create: bool):
    # Create an indexer
    indexer_name = f"{index_name}-indexer"
    skillset_name = f"{index_name}-skillset"
    data_source_name = f"{index_name}-blob"
    # data_source = create_data_source()
    # Create an IndexingParameters object with the executionEnvironment property
    indexing_parameters = IndexingParameters(
        configuration=IndexingParametersConfiguration(execution_environment=IndexerExecutionEnvironment.PRIVATE,
                                                      allow_skillset_to_read_file_data=True,
                                                      query_timeout=None)
    )
    indexer = SearchIndexer(
        name=indexer_name,
        description="Indexer to index documents and generate embeddings",
        skillset_name=skillset_name,
        target_index_name=index_name,
        data_source_name=data_source_name,  # data_source.name,
        parameters=indexing_parameters,
        #Map the metadata_storage_name field to the title field in the index to display the PDF title in the search results
        field_mappings=[FieldMapping(source_field_name="metadata_storage_name", target_field_name="title")]
    )

    if is_create:
        indexer_result = client.create_or_update_indexer(indexer)

    # Run the indexer
    client.run_indexer(indexer_name)
    print(f' {indexer_name} created, indexer_result {indexer_result}')


if __name__ == '__main__':
    # connect_to_blog()
    # create_data_source()
    create_search_index()
    create_skillset()
    create_indexer(True)
    # create_indexer(False)
