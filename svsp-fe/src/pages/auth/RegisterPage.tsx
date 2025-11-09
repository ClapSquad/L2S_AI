import { useForm } from "react-hook-form";
import styled from "styled-components";
import NavigationBar from "./components/NavigationBar";
import EmailInput from "./components/EmailInput";
import PasswordInput from "./components/PasswordInput";
import ConfirmPasswordInput from "./components/ConfirmPasswordInput";
import { useRegister } from "@auth/hooks/useRegister";
import UsernameInput from "./components/UsernameInput";

interface RegisterFormData {
  email: string;
  username: string;
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

  const { mutate } = useRegister();
  const onSubmit = (data: RegisterFormData) => {
    mutate({
      email: data.email,
      username: data.username,
      password: data.password,
    });
  };

  return (
    <PageFiller>
      <NavigationBar />
      <RegisterPageWrapper>
        <h2>회원가입</h2>
        <RegisterForm onSubmit={handleSubmit(onSubmit)}>
          <EmailInput register={register} errors={errors} />
          <UsernameInput register={register} errors={errors} />
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
