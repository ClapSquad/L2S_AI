import React, { useState, ChangeEvent } from "react";
import axios from "axios";

const FileUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);

  // ✅ 업로드 상태와 메시지 추가
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      // 파일을 새로 선택했을 때 이전 메시지 초기화
      setStatus("idle");
      setMessage("");
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setStatus("error");
      setMessage("파일을 선택하세요.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setStatus("uploading");
      setMessage("업로드 중...");

     await axios.post("/api/upload", formData);

      setStatus("success");
      setMessage("✅ 업로드 성공!");
    } catch (err) {
      console.error(err);
      setStatus("error");
      setMessage("❌ 업로드 실패. 다시 시도해주세요.");
    }
  };

  // ✅ 상태별 색상 설정
  const getMessageColor = () => {
    switch (status) {
      case "success":
        return "green";
      case "error":
        return "red";
      case "uploading":
        return "blue";
      default:
        return "black";
    }
  };

  return (
    <div style={{ padding: 20, textAlign: "center" }}>
      <h2>파일 업로드</h2>
      <input type="file" onChange={handleFileChange} />
      <button
        style={{ marginLeft: 10 }}
        onClick={handleUpload}
        disabled={!file}   // 파일이 없으면 버튼 비활성화
        >
        업로드
      </button>

      {/* ✅ 상태 메시지 표시 */}
      {message && (
        <p style={{ marginTop: 15, color: getMessageColor(), fontWeight: 500 }}>
          {message}
        </p>
      )}
    </div>
  );
};

export default FileUpload;
