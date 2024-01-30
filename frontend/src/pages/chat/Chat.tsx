import React, { useRef, useState, useEffect } from "react";
import { Stack } from "@fluentui/react";
import {
  BroomRegular,
  DismissRegular,
  SquareRegular,
} from "@fluentui/react-icons";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { v4 as uuidv4 } from "uuid";
import BBYConnect from "../../assets/BBYConnect.svg";
import styles from "./Chat.module.css";
import Azure from "../../assets/Azure.svg";

import {
  ChatMessage,
  ConversationRequest,
  conversationApi,
  customConversationApi,
  Citation,
  ToolMessageContent,
  ChatResponse,
} from "../../api";
import { Answer } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import {
  Dropdown,
  IDropdownOption,
  IDropdownStyles,
} from "@fluentui/react/lib/Dropdown";

const Chat = () => {
  const lastQuestionRef = useRef<string>("");
  const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [showLoadingMessage, setShowLoadingMessage] = useState<boolean>(false);
  const [activeCitation, setActiveCitation] =
    useState<
      [
        content: string,
        id: string,
        title: string,
        filepath: string,
        url: string,
        metadata: string
      ]
    >();
  const [isCitationPanelOpen, setIsCitationPanelOpen] =
    useState<boolean>(false);
  const [answers, setAnswers] = useState<ChatMessage[]>([]);
  const [displayAnswer, setDisplayAnswer] = useState<ChatMessage[]>([]);
  const abortFuncs = useRef([] as AbortController[]);
  const [conversationId, setConversationId] = useState<string>(uuidv4());

  const makeApiRequest = async (question: string) => {
    lastQuestionRef.current = question;

    setIsLoading(true);
    setDisplayAnswer([]);
    setShowLoadingMessage(true);
    const abortController = new AbortController();
    abortFuncs.current.unshift(abortController);

    const userMessage: ChatMessage = {
      role: "user",
      content: question,
    };

    const request: ConversationRequest = {
      id: conversationId,
      messages: [...answers, userMessage],
    };

    let result = {} as ChatResponse;
    try {
      const response = await customConversationApi(
        request,
        abortController.signal,
        selectedEmployeeNumber
      );
      if (response?.body) {
        const reader = response.body.getReader();
        let runningText = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          var text = new TextDecoder("utf-8").decode(value);
          const objects = text.split("\n");
          objects.forEach((obj) => {
            try {
              runningText += obj;
              result = JSON.parse(runningText);
              setShowLoadingMessage(false);
              setAnswers([
                ...answers,
                userMessage,
                ...result.choices[0].messages,
              ]);
              setDisplayAnswer(result.choices[0].messages);
              runningText = "";
            } catch {}
          });
        }
        setAnswers([...answers, userMessage, ...result.choices[0].messages]);
        setDisplayAnswer(result.choices[0].messages);
      }
    } catch (e) {
      if (!abortController.signal.aborted) {
        console.error(result);
        alert(
          "An error occurred. Please try again. If the problem persists, please contact the site administrator."
        );
      }
      setAnswers([...answers, userMessage]);
    } finally {
      setIsLoading(false);
      setShowLoadingMessage(false);
      abortFuncs.current = abortFuncs.current.filter(
        (a) => a !== abortController
      );
    }

    return abortController.abort();
  };

  const clearChat = () => {
    lastQuestionRef.current = "";
    setActiveCitation(undefined);
    setAnswers([]);
    setConversationId(uuidv4());
  };

  const stopGenerating = () => {
    abortFuncs.current.forEach((a) => a.abort());
    setShowLoadingMessage(false);
    setIsLoading(false);
  };

  useEffect(
    () => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" }),
    [showLoadingMessage]
  );

  const onShowCitation = (citation: Citation) => {
    setActiveCitation([
      citation.content,
      citation.id,
      citation.title ?? "",
      citation.filepath ?? "",
      "",
      "",
    ]);
    setIsCitationPanelOpen(true);
  };

  const parseCitationFromMessage = (message: ChatMessage) => {
    if (message.role === "tool") {
      try {
        const toolMessage = JSON.parse(message.content) as ToolMessageContent;
        return toolMessage.citations;
      } catch {
        return [];
      }
    }
    return [];
  };

  const [selectedEmployeeNumber, setSelectedEmployeeNumberValue] =
    React.useState<string | number | undefined>(940931);
  const handleDropdownChange = (
    event: React.FormEvent<HTMLDivElement>,
    option?: IDropdownOption
  ): void => {
    if (option) {
      setSelectedEmployeeNumberValue(option.key as string);
    }
  };
  const dropdownStyles: Partial<IDropdownStyles> = {
    dropdown: { width: 200 },
  };

  const options: IDropdownOption[] = [
    { key: "449037", text: "449037" },
    { key: "1447793", text: "1447793" },
    { key: "1621171", text: "1621171" },
    { key: "940931", text: "940931" },
    { key: "49124", text: "49124" },
    { key: "122685", text: "122685" },
    { key: "248878", text: "248878" },
    { key: "315035", text: "315035" },
    { key: "597533", text: "597533" },
    { key: "832479", text: "832479" },
    { key: "1388776", text: "1388776" },
    { key: "1538546", text: "1538546" },
    { key: "1560351", text: "1560351" },
    { key: "3001030", text: "3001030" },
    { key: "108554", text: "108554" },
    { key: "158623", text: "158623" },
  ];

  const clearAndHandleDropdownChange = (
    event: React.FormEvent<HTMLDivElement>,
    option?: IDropdownOption
  ): void => {
    handleDropdownChange(event, option);
    clearChat();
  };
  return (
    <>
      <header className={styles.header} role={"banner"}>
        <div className={styles.headerContainer}>
          <Stack horizontal verticalAlign="center">
            <img
              src={BBYConnect}
              className={styles.headerIcon}
              aria-hidden="true"
            />
            <div className={styles.dropdownContainer}>
              <Dropdown
                placeholder="940931"
                defaultSelectedKey={"940931"}
                selectedKey={selectedEmployeeNumber}
                options={options}
                onChange={clearAndHandleDropdownChange}
                styles={dropdownStyles}
              />
            </div>
          </Stack>
        </div>
      </header>
      <div className={styles.container}>
        <Stack horizontal className={styles.chatRoot}>
          <div className={styles.chatContainer}>
            <Stack className={styles.chatInput}>
              {/* <BroomRegular
                className={styles.clearChatBroom}
                style={{
                  background:
                    isLoading || answers.length === 0
                      ? "#BDBDBD"
                      : "radial-gradient(109.81% 107.82% at 100.1% 90.19%, #0F6CBD 33.63%, #2D87C3 70.31%, #8DDDD8 100%)",
                  cursor: isLoading || answers.length === 0 ? "" : "pointer",
                }}
                onClick={clearChat}
                onKeyDown={(e) =>
                  e.key === "Enter" || e.key === " " ? clearChat() : null
                }
                aria-label="Clear session"
                role="button"
                tabIndex={0}
              /> */}
              <div
                style={{
                  padding: "1rem",
                  fontWeight: 700,
                  fontSize: "24px",
                  lineHeight: "30px",
                }}
              >
                Lets find what you need.
              </div>
              <QuestionInput
                clearOnSend
                placeholder="Type a new question..."
                disabled={isLoading}
                onSend={(question) => makeApiRequest(question)}
              />
            </Stack>
            {isLoading && (
              <Stack
                horizontal
                className={styles.stopGeneratingContainer}
                role="button"
                aria-label="Stop generating"
                tabIndex={0}
                onClick={stopGenerating}
                onKeyDown={(e) =>
                  e.key === "Enter" || e.key === " " ? stopGenerating() : null
                }
              >
                <SquareRegular
                  className={styles.stopGeneratingIcon}
                  aria-hidden="true"
                />
                <span className={styles.stopGeneratingText} aria-hidden="true">
                  Stop generating
                </span>
              </Stack>
            )}
            {!lastQuestionRef.current ? null : (
              <div
                className={styles.chatMessageStream}
                style={{ marginBottom: isLoading ? "40px" : "0px" }}
              >
                {answers.map((answer, index) => (
                  <>
                    {answer.role === "user" ? (
                      <div className={styles.chatMessageUser}>
                        <div className={styles.chatMessageUserMessage}>
                          {answer.content}
                        </div>
                      </div>
                    ) : answer.role === "assistant" ? (
                      <div className={styles.chatMessageGpt}>
                        <Answer
                          answer={{
                            answer: answer.content,
                            citations: parseCitationFromMessage(
                              answers[index - 1]
                            ),
                          }}
                          onCitationClicked={(c) => onShowCitation(c)}
                        />
                      </div>
                    ) : null}
                  </>
                ))}
                {showLoadingMessage && (
                  <>
                    <div className={styles.chatMessageUser}>
                      <div className={styles.chatMessageUserMessage}>
                        {lastQuestionRef.current}
                      </div>
                    </div>
                    <div className={styles.chatMessageGpt}>
                      <Answer
                        answer={{
                          answer: "Generating answer...",
                          citations: [],
                        }}
                        onCitationClicked={() => null}
                      />
                    </div>
                  </>
                )}
                <div ref={chatMessageStreamEnd} />
              </div>
            )}
          </div>
          {answers.length > 0 && isCitationPanelOpen && activeCitation && (
            <Stack.Item className={styles.citationPanel}>
              <Stack
                horizontal
                className={styles.citationPanelHeaderContainer}
                horizontalAlign="space-between"
                verticalAlign="center"
              >
                <span className={styles.citationPanelHeader}>Citations</span>
                <DismissRegular
                  className={styles.citationPanelDismiss}
                  onClick={() => setIsCitationPanelOpen(false)}
                />
              </Stack>
              <h5 className={styles.citationPanelTitle}>{activeCitation[2]}</h5>
              <ReactMarkdown
                className={styles.citationPanelContent}
                children={activeCitation[0]}
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
              />
            </Stack.Item>
          )}
        </Stack>
      </div>
    </>
  );
};
export default Chat;