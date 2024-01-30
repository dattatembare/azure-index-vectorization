import logging
import os

from dotenv import load_dotenv
from langchain.callbacks import get_openai_callback
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory, ConversationBufferWindowMemory, \
    CombinedMemory
from langchain.prompts import PromptTemplate
from opencensus.ext.azure.log_exporter import AzureLogHandler

from ..common.Answer import Answer
from ..common.SourceDocument import SourceDocument
from ..helpers.AzureBlobStorageHelper import AzureBlobStorageClient
from ..helpers.AzureSearchHelper import AzureSearchHelper
from ..helpers.ConfigHelper import ConfigHelper
from ..helpers.EnvHelper import EnvHelper
from ..helpers.LLMHelper import LLMHelper

# Setting logging
load_dotenv()
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(connection_string=os.getenv('APPINSIGHTS_CONNECTION_STRING',
                                                              'InstrumentationKey=7d33b306-9fae-4ff7-9455-16ce26e296b5;IngestionEndpoint=https://eastus2-0.in.applicationinsights.azure.com/;LiveEndpoint=https://eastus2.livediagnostics.monitor.azure.com/')))
logger.setLevel(logging.INFO)


class ConversationalChainTool:
    def __init__(self):
        env_helper: EnvHelper = EnvHelper()
        vector_store_helper: AzureSearchHelper = AzureSearchHelper()

        self.llm = LLMHelper().get_llm()
        self.embeddings = LLMHelper().get_embedding_model()
        self.vector_store = vector_store_helper.get_vector_store()
        self.blob_client = AzureBlobStorageClient()

    def get_answer_using_langchain(self, question, chat_history):
        chat_template = """
            Answer the question based on the chat history(delimited by <hs></hs>) and context(delimited by <ctx> </ctx>) below.
            -----------
            <ctx>
            {context}
            </ctx>
            -----------
            <hs>
            {chat_history}
            </hs>
            -----------
            Question: {question}
            Answer: 
            """

        prompt_history = PromptTemplate(input_variables=["context", "question", "chat_history"], template=chat_template)

        chat_memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="question",
            output_key='answer',
            return_messages=True
        )
        self.qa = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(),
            chain_type="stuff",
            return_source_documents=True,
            verbose=True,
            combine_docs_chain_kwargs={'prompt': prompt_history},
            memory=chat_memory,
        )

        response = self.qa(question, context="PTO (Plan 1)", question=question)

        with get_openai_callback() as cb:
            req_args = {"question": question, "chat_history": chat_history, "context": "PTO (Plan 1)"}
            result = self.qa(req_args)

        # config = ConfigHelper.get_active_config_or_default()

        # TODO: check if question is safe
        # new_template = """
        # You help everyone by answering questions, and improve your answers from previous answers in History.
        # Don't try to make up an answer, if you don't know, just say that you don't know.
        # Answer in the same language the question was asked.
        # Answer in a way that is easy to understand.
        # Do not say "Based on the information you provided, ..." or "I think the answer is...". Just answer the question directly in detail.
        #
        # History: {chat_history}
        #
        # Context: {context}
        #
        # Question: {question}
        # Answer:
        # """
        #
        # # condense_question_prompt = PromptTemplate(template=config.prompts.condense_question_prompt, input_variables=["question", "chat_history"])
        # condense_question_prompt = PromptTemplate(template=new_template,
        #                                           input_variables=["question", "chat_history", "context"])
        # answering_prompt = PromptTemplate(template=config.prompts.answering_prompt,
        #                                   input_variables=["question", "sources"])
        # # answering_prompt = PromptTemplate(template=config.prompts.answering_prompt, input_variables=["question", "context"])
        #
        # question_generator = LLMChain(llm=self.llm, prompt=condense_question_prompt, verbose=True)
        #
        # doc_chain = load_qa_with_sources_chain(
        #     self.llm,
        #     chain_type="stuff",
        #     prompt=answering_prompt,
        #     document_variable_name="sources",
        #     verbose=True
        # )
        # conv_memory = ConversationBufferWindowMemory(
        #     memory_key="chat_history",
        #     question_key="question",
        #     output_key="answer",
        #     context_key="context",
        #     return_messages=True,
        #     k=1
        # )
        # summary_memory = ConversationSummaryMemory(llm=self.llm, question_key="question", output_key='answer')
        # chat_history = CombinedMemory(memories=[conv_memory, summary_memory])
        #
        # chain = ConversationalRetrievalChain(
        #     retriever=self.vector_store.as_retriever(),
        #     question_generator=question_generator,
        #     combine_docs_chain=doc_chain,
        #     return_source_documents=True,
        #     return_generated_question=True,
        #     memory=chat_history,
        #     get_chat_history=lambda h: h,
        #     combine_docs_chain_kwargs={'prompt': condense_question_prompt}
        # )
        #
        # with get_openai_callback() as cb:
        #     req_args = {"question": question, "chat_history": chat_history, "context": "PTO (Plan 1)"}
        #     result = chain(req_args)
        #     # result = chain.from_llm(llm=self.llm, retriever=self.vector_store.as_retriever())
        #     # result = chain({"question": question, "chat_history": chat_history})
        #     # result = chain({"question": question, "chat_history": chat_history, "context": "PTO (Plan 1)"})

        answer = result['answer'].replace('  ', ' ')
        print(f"answer: {answer}")
        # Generate Answer Object
        source_documents = []
        for source in result['source_documents']:
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

    def handle_question(self, question, chat_history):
        result = self.get_answer_using_langchain(question, chat_history)
        return result
