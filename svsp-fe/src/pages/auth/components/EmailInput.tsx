import type { FieldErrors, UseFormRegister } from "react-hook-form";

interface EmailInputProps {
  register: UseFormRegister<any>;
  errors: FieldErrors;
}

export default function EmailInput({ register, errors }: EmailInputProps) {
  return (
    <>
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
        <p style={{ color: "red" }}>{errors.email.message?.toString()}</p>
      )}
    </>
  );
}
