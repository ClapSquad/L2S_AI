import React, { useState } from "react";

const FileUpload: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setMessage("");
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setMessage("파일을 선택하세요.");
      return;
    }

    setUploading(true);
    setMessage("");

    try {
      // 예시: 서버에 업로드 (백엔드 주소 바꾸세요)
      const formData = new FormData();
      formData.append("file", selectedFile);

    const response = await fetch(`${import.meta.env.VITE_API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        setMessage("✅ 업로드 성공!");
      } else {
        setMessage("❌ 업로드 실패");
      }
    } catch (error) {
      console.error(error);
      setMessage("❌ 업로드 중 오류 발생");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ padding: "20px", border: "1px solid #ddd", borderRadius: "8px", width: "300px" }}>
      <h3>파일 업로드</h3>
      <input type="file" onChange={handleFileChange} />
      <button
        style={{ marginLeft: "10px" }}
        onClick={handleUpload}
        disabled={uploading}
      >
        {uploading ? "업로드 중..." : "업로드"}
      </button>
      {message && <p style={{ marginTop: "10px" }}>{message}</p>}
    </div>
  );
};

export default FileUpload;
