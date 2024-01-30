from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents._generated.models import RawVectorQuery
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryLanguage,
    QueryType,
    VectorizableTextQuery,
)

from backend.utilities.helpers.EnvHelper import EnvHelper

env_helper = EnvHelper()


def vector_search(query: str, search_type: str = 'hybrid'):
    """
    Perform a hybrid search + semantic reranking
    :param search_type:
    :param query:
    :return:
    """

    service_endpoint = env_helper.AZURE_SEARCH_SERVICE
    index_name = env_helper.AZURE_SEARCH_INDEX
    key = env_helper.AZURE_SEARCH_KEY
    credential = AzureKeyCredential(key)
    search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=credential)
    vector_query = VectorizableTextQuery(text=query, k=2, fields="content_vector", exhaustive=True)

    if 'vector' == search_type:
        # Pure Vector Search
        # Use the below query to pass in the raw vector query instead of the query vectorization
        # from azure.search.documents._generated.models import RawVectorQuery
        # vector_query = RawVectorQuery(vector=generate_embeddings(query), k=2, fields="content_vector")

        results = search_client.search(
            search_text=None,
            vector_queries=[vector_query],
            select=["parent_id", "content_id", "content"],
            top=4
        )

    elif 'hybrid' == search_type:
        # Hybrid Search
        results = search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            select=["parent_id", "id", "content", "title", "metadata", "source", "offset", "chunk"],
            top=4
        )

    elif 'semantic_hybrid' == search_type:
        # Semantic Hybrid Search
        results = search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            select=["parent_id", "id", "content", "title"],
            query_type=QueryType.SEMANTIC, query_language=QueryLanguage.EN_US,
            semantic_configuration_name='my-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE,
            query_answer=QueryAnswerType.EXTRACTIVE,
            top=4
        )

    semantic_answers = results.get_answers()
    if semantic_answers:
        for answer in semantic_answers:
            if answer.highlights:
                print(f"Semantic Answer: {answer.highlights}")
            else:
                print(f"Semantic Answer: {answer.text}")
            print(f"Semantic Answer Score: {answer.score}\n")

    for result in results:
        print(f"title: {result['title']}")
        print(f"parent_id: {result['parent_id']}")
        print(f"id: {result['id']}")
        print(f"Score: {result['@search.score']}")
        print(f"Score: {result['@search.reranker_score']}")
        print(f"Content: {result['content']}")

        captions = result["@search.captions"]
        if captions:
            caption = captions[0]
            if caption.highlights:
                print(f"Caption highlights: {caption.highlights}\n")
            else:
                print(f"Caption text: {caption.text}\n")


# Function to generate embeddings for title and content fields, also used for query embeddings
def generate_embeddings(text, model="text-embedding-ada-002"):
    import openai

    openai.api_type = "azure"
    openai.api_key = env_helper.AZURE_OPENAI_KEY
    openai.api_base = env_helper.OPENAI_API_BASE
    openai.api_version = "2023-05-15"

    response = openai.Embedding.create(
        input="How do I use Python in VSCode?",
        engine="text-embedding-ada-002"
    )
    return response['data'][0]['embedding']
    # print(embeddings)


if __name__ == '__main__':
    # _search_type = "vector"
    _search_type = "hybrid"
    # _search_type = "semantic_hybrid"
    vector_search(query="What is SKU needed to mount a 55 inch smaller TV?", search_type=_search_type)
    # vector_search(query="What is PTO(Plan 1)?", search_type=_search_type)
    # vector_search(query="What are the details of Paid Time Off Policy Plan 1 and Sick leave Plan 40?", search_type=_search_type)
    # vector_search(query="What are the details of Sick(Plan 40)?", search_type=_search_type)
    # vector_search(query="What is Sick(Plan 40)?", search_type=_search_type)
    # vector_search(query="PTO", search_type=_search_type)
