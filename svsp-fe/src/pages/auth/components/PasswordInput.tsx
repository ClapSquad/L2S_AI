import type { FieldErrors, UseFormRegister } from "react-hook-form";

interface PasswordInputProps {
  register: UseFormRegister<any>;
  errors: FieldErrors;
}

export default function PasswordInput({
  register,
  errors,
}: PasswordInputProps) {
  return (
    <>
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
        <p style={{ color: "red" }}>{errors.password.message?.toString()}</p>
      )}
    </>
  );
}
