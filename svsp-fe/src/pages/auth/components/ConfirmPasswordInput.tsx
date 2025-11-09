import type { FieldErrors, UseFormRegister } from "react-hook-form";

interface ConfirmPasswordInputProps {
  register: UseFormRegister<any>;
  errors: FieldErrors;
  password: string;
}

export default function ConfirmPasswordInput({
  register,
  errors,
  password,
}: ConfirmPasswordInputProps) {
  return (
    <>
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
        <p style={{ color: "red" }}>
          {errors.confirmPassword.message?.toString()}
        </p>
      )}
    </>
  );
}
