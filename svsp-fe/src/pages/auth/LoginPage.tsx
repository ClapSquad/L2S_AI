import { useForm } from "react-hook-form";
import styled from "styled-components";
import { Link } from "react-router-dom";
import routePath from "@router/routePath";
import EmailInput from "./components/EmailInput";
import PasswordInput from "./components/PasswordInput";
import { useLogin } from "@auth/hooks/useLogin";
import NavigationBar from "@components/NavigationBar";
import { useRejectLoggedInUser } from "./hooks/useRejectLoggedInUser";

interface LoginFormData {
  email: string;
  password: string;
}

export default function LoginPage() {
  useRejectLoggedInUser();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>();

  const { mutate } = useLogin();
  const onSubmit = (data: LoginFormData) => {
    mutate(data);
  };

  return (
    <PageFiller>
      <NavigationBar />
      <LoginPageWrapper>
        <h2>로그인</h2>
        <LoginForm onSubmit={handleSubmit(onSubmit)}>
          <EmailInput register={register} errors={errors} />
          <PasswordInput register={register} errors={errors} />
          <button type="submit">로그인</button>
        </LoginForm>
        <Link to={routePath.REGISTER}>계정 생성하기</Link>
      </LoginPageWrapper>
    </PageFiller>
  );
}

const LoginForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

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
