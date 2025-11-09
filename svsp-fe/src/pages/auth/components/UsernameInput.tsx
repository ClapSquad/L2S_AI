import type { FieldErrors, UseFormRegister } from "react-hook-form";

interface UserNameInputProps {
  register: UseFormRegister<any>;
  errors: FieldErrors;
}

export default function UsernameInput({
  register,
  errors,
}: UserNameInputProps) {
  return (
    <>
      <input
        {...register("username", {
          required: "이메일을 입력해주세요.",
          minLength: {
            value: 2,
            message: "이름은 최소 2자 이상이어야 합니다.",
          },
          validate: (value) =>
            value.trim() !== "" || "공백만 입력할 수 없습니다.",
        })}
        placeholder="이름"
        type="text"
      />
      {errors.email && (
        <p style={{ color: "red" }}>{errors.email.message?.toString()}</p>
      )}
    </>
  );
}
