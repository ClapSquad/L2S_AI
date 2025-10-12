import React from "react";
import { useForm } from "react-hook-form";

interface RegisterFormData {
  email: string;
  password: string;
  confirmPassword: string;
}

const RegisterPage: React.FC = () => {
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
    <div>
      <h2>회원가입</h2>
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
              value: 8,
              message: "비밀번호는 최소 8자 이상이어야 합니다.",
            },
            pattern: {
              value: /^(?=.*[!@#$%^&*(),.?":{}|<>]).*$/,
              message: "비밀번호에는 특수문자가 포함되어야 합니다.",
            },
          })}
          placeholder="비밀번호"
          type="password"
        />
        {errors.password && (
          <p style={{ color: "red" }}>{errors.password.message}</p>
        )}
        <br />

        <input
          {...register("confirmPassword", {
            required: "비밀번호 확인을 입력해주세요.",
            validate: (value) =>
              value === password || "비밀번호가 일치하지 않습니다.",
          })}
          placeholder="비밀번호 확인"
          type="password"
        />
        {errors.confirmPassword && (
          <p style={{ color: "red" }}>{errors.confirmPassword.message}</p>
        )}
        <br />

        <button type="submit">회원가입</button>
      </form>
    </div>
  );
};

export default RegisterPage;
