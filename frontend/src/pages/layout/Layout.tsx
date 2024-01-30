import { createContext } from "react";
import { Outlet, Link } from "react-router-dom";
import styles from "./Layout.module.css";
import BBYConnect from "../../assets/BBYConnect.svg";
import { CopyRegular, ShareRegular } from "@fluentui/react-icons";
import { Dialog, Dropdown, Stack, TextField } from "@fluentui/react";
import { useEffect, useState } from "react";

const Layout = () => {
  const [isSharePanelOpen, setIsSharePanelOpen] = useState<boolean>(false);
  const [copyClicked, setCopyClicked] = useState<boolean>(false);
  const [copyText, setCopyText] = useState<string>("Copy URL");

  const handleShareClick = () => {
    setIsSharePanelOpen(true);
  };

  const handleSharePanelDismiss = () => {
    setIsSharePanelOpen(false);
    setCopyClicked(false);
    setCopyText("Copy URL");
  };

  const handleCopyClick = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopyClicked(true);
  };

  useEffect(() => {
    if (copyClicked) {
      setCopyText("Copied URL");
    }
  }, [copyClicked]);

  return (
    <div className={styles.layout}>
      <Outlet />
    </div>
  );
};

export default Layout;