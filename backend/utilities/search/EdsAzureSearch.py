import json
from typing import Any, List, Dict

from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryLanguage,
    QueryType,
    VectorizableTextQuery,
)
from langchain_core.documents import Document
from langchain_core.utils import get_from_env

# Allow overriding field names for Azure Search
FIELDS_ID = get_from_env(
    key="AZURESEARCH_FIELDS_ID", env_key="AZURESEARCH_FIELDS_ID", default="content_id"
)
FIELDS_CONTENT = get_from_env(
    key="AZURESEARCH_FIELDS_CONTENT",
    env_key="AZURESEARCH_FIELDS_CONTENT",
    default="content",
)
FIELDS_CONTENT_VECTOR = get_from_env(
    key="AZURESEARCH_FIELDS_CONTENT_VECTOR",
    env_key="AZURESEARCH_FIELDS_CONTENT_VECTOR",
    default="content_vector",
)
FIELDS_METADATA = get_from_env(
    key="AZURESEARCH_FIELDS_TAG", env_key="AZURESEARCH_FIELDS_TAG", default="metadata"
)


class EdsAzureSearch:
    def __init__(self):
        pass

    def similarity_search(self, search_client, query: str, k: int = 2, **kwargs: Any) -> List[Document]:
        search_type = kwargs.get("search_type", "hybrid")
        vector_query = VectorizableTextQuery(text=query, k=k, fields="content_vector", exhaustive=True)

        if 'vector' == search_type:
            # Pure Vector Search
            # Use the below query to pass in the raw vector query instead of the query vectorization
            # vector_query = RawVectorQuery(vector=generate_embeddings(query), k=2, fields="content_vector")

            results = search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                select=["parent_id", "content_id", "content"],
                top=k
            )

        elif 'hybrid' == search_type:
            # Hybrid Search
            results = search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                select=["parent_id", "content_id", "content"],
                top=k
            )

        elif 'semantic_hybrid' == search_type:
            # Semantic Hybrid Search
            results = search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                select=["parent_id", "content_id", "content"],
                query_type=QueryType.SEMANTIC, query_language=QueryLanguage.EN_US,
                semantic_configuration_name='my-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE,
                query_answer=QueryAnswerType.EXTRACTIVE,
                top=k
            )
        else:
            raise ValueError(f"search_type of {search_type} not allowed.")

        # Print Results
        # self.return_docs(results)

        # Get Semantic Answers
        semantic_answers = results.get_answers() or []
        semantic_answers_dict: Dict = {}
        for semantic_answer in semantic_answers:
            semantic_answers_dict[semantic_answer.key] = {
                "text": semantic_answer.text,
                "highlights": semantic_answer.highlights,
            }

        # return [
        #     SourceDocument(
        #         content=result['content'],
        #         source="source",
        #         id="1",
        #         title="title",
        #         chunk=0,
        #         offset=0,
        #         page_number=1,
        #     ) for result in results
        # ]

        # Convert results to Document objects
        # return [
        docs = []
        for result in results:
            docs.append(
                Document(
                    page_content=result.pop(FIELDS_CONTENT),
                    metadata={
                        **({FIELDS_ID: result.pop(FIELDS_ID)} if FIELDS_ID in result else {}),
                        **(
                            json.loads(result.get(FIELDS_METADATA, {}))
                            if FIELDS_METADATA in result
                            else {k: v for k, v in result.items() if k != FIELDS_CONTENT_VECTOR}
                        ),
                        **{
                            "captions": {
                                "text": result.get("@search.captions", [{}])[0].text,
                                "highlights": result.get("@search.captions", [{}])[
                                    0
                                ].highlights,
                            }
                            if result.get("@search.captions")
                            else {},
                            "answers": semantic_answers_dict.get(
                                json.loads(result.get(FIELDS_METADATA, "{}")).get("key"), ""
                            ),
                        },
                    },
                )
            )
        #     for result in results
        # ]
        return docs

    def return_docs(self, results):
        semantic_answers = results.get_answers()
        if semantic_answers:
            for answer in semantic_answers:
                if answer.highlights:
                    print(f"Semantic Answer: {answer.highlights}")
                else:
                    print(f"Semantic Answer: {answer.text}")
                print(f"Semantic Answer Score: {answer.score}\n")

        for result in results:
            print(f"parent_id: {result['parent_id']}")
            print(f"content_id: {result['content_id']}")
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
