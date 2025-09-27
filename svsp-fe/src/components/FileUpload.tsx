import React, { useState, ChangeEvent } from "react";
import axios from "axios";

const FileUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return alert("파일을 선택하세요.");
    const formData = new FormData();
    formData.append("file", file);

    try {
      await axios.post("/api/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      alert("업로드 성공!");
    } catch (err) {
      console.error(err);
      alert("업로드 실패");
    }
  };

  return (
    <div style={{ padding: 20, textAlign: "center" }}>
      <h2>파일 업로드</h2>
      <input type="file" onChange={handleFileChange} />
      <button style={{ marginLeft: 10 }} onClick={handleUpload}>
        업로드
      </button>
    </div>
  );
};

export default FileUpload;
