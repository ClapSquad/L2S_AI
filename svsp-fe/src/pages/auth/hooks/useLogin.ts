import routePath from "@router/routePath";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import { useContext } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { axiosInstance } from "src/apis/axiosInstance";
import { API } from "src/apis/endpoints";
import { AuthContext } from "src/contexts/AuthContext";
import queryClient from "src/apis/queryClient";
import type { UserInfoResponse } from "./useMe";

interface LoginRequest {
  email: string;
  password: string;
}

interface LoginResponse {
  message: string;
}

export function useLogin() {
  const navigate = useNavigate();
  const { setUser } = useContext(AuthContext);

  return useMutation<LoginResponse, Error, LoginRequest>({
    mutationFn: async (data) => {
      const res = await axiosInstance.post(API.AUTH.LOGIN, data);
      return res.data;
    },
    onSuccess: async (_data) => {
      toast.success("로그인 되었습니다.");
      navigate(routePath.HOME);

      const me = await queryClient.fetchQuery<UserInfoResponse>({
        queryKey: ["me"],
        queryFn: async () => {
          const res = await axiosInstance.get(API.AUTH.ME);
          return res.data;
        },
      });
      setUser({
        email: me.user.email,
        username: me.user.username,
      });
    },
    onError: (error: any) => {
      if (axios.isAxiosError(error)) {
        const message =
          error.response?.data?.detail || "로그인에 실패했습니다.";
        toast.error(`❌ ${message}`);
      } else {
        toast.error("예상치 못한 오류가 발생했습니다.");
      }
    },
  });
}
