import { useForm } from "react-hook-form";
import styled from "styled-components";
import NavigationBar from "./components/NavigationBar";
import EmailInput from "./components/EmailInput";
import PasswordInput from "./components/PasswordInput";
import ConfirmPasswordInput from "./components/ConfirmPasswordInput";

interface RegisterFormData {
  email: string;
  password: string;
  confirmPassword: string;
}

export default function RegisterPage() {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormData>();
  const password = watch("password");

  const onSubmit = (data: RegisterFormData) => {
    alert(`회원가입 완료: ${data.email}`);
  };

  return (
    <PageFiller>
      <NavigationBar />
      <RegisterPageWrapper>
        <h2>회원가입</h2>
        <RegisterForm onSubmit={handleSubmit(onSubmit)}>
          <EmailInput register={register} errors={errors} />
          <PasswordInput register={register} errors={errors} />
          <ConfirmPasswordInput
            register={register}
            errors={errors}
            password={password}
          />
          <button type="submit">회원가입</button>
        </RegisterForm>
      </RegisterPageWrapper>
    </PageFiller>
  );
}

const RegisterForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const RegisterPageWrapper = styled.div`
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
