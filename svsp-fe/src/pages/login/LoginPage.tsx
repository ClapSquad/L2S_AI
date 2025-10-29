import axios from "axios";
axios.defaults.withCredentials = true;
import React from "react";
import { useForm } from "react-hook-form";

interface LoginFormData {
  email: string;
  password: string;
}

const LoginPage: React.FC = () => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>();

  const onSubmit = async (data: LoginFormData) => {
    try {
      const res = await axios.post("http://127.0.0.1:8000/auth/login", data);
      alert("로그인 성공!");
      console.log(res.data); // for debugging
    } catch (err: any) {
      console.error(err);
      alert("로그인 실패. 이메일 또는 비밀번호를 확인해주세요.");
    }
  };
  

  return (
    <div>
      <h2>로그인</h2>
      <form onSubmit={handleSubmit(onSubmit)}>
        <input
          {...register("email", {
            required: "이메일을 입력해주세요.",
            pattern: {
              value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
              message: "유효한 이메일 형식이 아닙니다.",
            },
          })}
          placeholder="이메일"
          type="email"
        />
        {errors.email && <p style={{ color: "red" }}>{errors.email.message}</p>}
        <br />

        <input
          {...register("password", {
            required: "비밀번호를 입력해주세요.",
            minLength: {
              value: 6,
              message: "비밀번호는 최소 6자 이상이어야 합니다.",
            },
          })}
          placeholder="비밀번호"
          type="password"
        />
        {errors.password && (
          <p style={{ color: "red" }}>{errors.password.message}</p>
        )}
        <br />

        <button type="submit">로그인</button>
      </form>
    </div>
  );
};

export default LoginPage;
