import { useForm } from "react-hook-form";
import NavigationBar from "./components/NavigationBar";
import styled from "styled-components";
import { Link } from "react-router-dom";
import routePath from "@router/routePath";

interface LoginFormData {
  email: string;
  password: string;
}

export default function LoginPage() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>();

  const onSubmit = (data: LoginFormData) => {
    alert(`로그인 시도: ${data.email}`);
  };

  return (
    <PageFiller>
      <NavigationBar />
      <LoginPageWrapper>
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
          {errors.email && (
            <p style={{ color: "red" }}>{errors.email.message}</p>
          )}
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
        <Link to={routePath.REGISTER}>계정 생성하기</Link>
      </LoginPageWrapper>
    </PageFiller>
  );
}

const LoginPageWrapper = styled.div`
  flex-grow: 0.9;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
`;

const PageFiller = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
`;
