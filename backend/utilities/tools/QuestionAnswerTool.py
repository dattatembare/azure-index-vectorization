from typing import List
from .AnsweringToolBase import AnsweringToolBase

from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.callbacks import get_openai_callback

from ..helpers.AzureSearchHelper import AzureSearchHelper
from ..helpers.ConfigHelper import ConfigHelper
from ..helpers.LLMHelper import LLMHelper
from ..common.Answer import Answer
from ..common.SourceDocument import SourceDocument


class QuestionAnswerTool(AnsweringToolBase):
    def __init__(self) -> None:
        self.name = "QuestionAnswer"
        self.vector_store = AzureSearchHelper().get_vector_store()
        self.verbose = True
    
    def answer_question(self, question: str, chat_history: List[dict], **kwargs: dict):
        config = ConfigHelper.get_active_config_or_default()
        answering_prompt = PromptTemplate(template=config.prompts.answering_prompt, input_variables=["question", "sources"])
        llm_helper = LLMHelper()
        # Retrieve documents as sources
        try:
            sources = self.vector_store.similarity_search(query=question, k=4, search_type="hybrid")
        except Exception as e:
            print(f"\n answer_question: Exception while calling cognitive search engine. error: {e}")
            error_answer = Answer(question=question,
                                  answer="The information is not available in the knowledge base.",
                                  source_documents=[],
                                  prompt_tokens=0,
                                  completion_tokens=0)
            return error_answer

        # if 'questions_to_search_engine' in kwargs:
        #     sources = []
        #     for q in kwargs['questions_to_search_engine']:
        #         print(f"Question to Cog search: {q}")
        #         for s in self.vector_store.similarity_search(query=q, k=1, search_type="hybrid"):
        #             sources.append(s)
        # else:
        #     sources = self.vector_store.similarity_search(query=question, k=4, search_type="hybrid")
        
        # Generate answer from sources
        answer_generator = LLMChain(llm=llm_helper.get_llm(), prompt=answering_prompt, verbose=self.verbose)
        _start = 0
        if 'employee_data' in kwargs:
            _start = 1
        sources_text = "\n\n".join([f"[doc{i+1}]: {source.page_content}" for i, source in enumerate(sources, start=_start)])
        source_documents = []
        if 'employee_data' in kwargs:
            content = f"<p>[doc1]: {kwargs['employee_data']}</p>"
            content = content.replace('your', 'user')
            sources_text = f"{content}{sources_text}"
            source_documents = [SourceDocument(content=content, source='Employee Data')]

        # print(f"Question to LLM: {question}")
        with get_openai_callback() as cb:
            result = answer_generator({"question": question, "sources": sources_text})
            
        answer = result["text"]
        # print(f"Answer: {answer}")
                    
        # Generate Answer Object
        for source in sources:
            source_document = SourceDocument(
                id=source.metadata["id"],
                content=source.page_content,
                title=source.metadata["title"],
                source=source.metadata["source"],
                chunk=source.metadata["chunk"],
                offset=source.metadata["offset"],
                page_number=source.metadata["page_number"],
            )
            source_documents.append(source_document)
        
        clean_answer = Answer(question=question,
                              answer=answer,
                              source_documents=source_documents,
                              prompt_tokens=cb.prompt_tokens,
                              completion_tokens=cb.completion_tokens)
        return clean_answer
    