import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import { useContext } from "react";
import { toast } from "react-toastify";
import { axiosInstance } from "src/apis/axiosInstance";
import { API } from "src/apis/endpoints";
import { AuthContext } from "src/contexts/AuthContext";

export function useLogout() {
  const { setUser } = useContext(AuthContext);

  return useMutation({
    mutationFn: async () => {
      const res = await axiosInstance.post(API.AUTH.LOGOUT);
      return res.data;
    },
    onSuccess: async (_data) => {
      toast.success("로그아웃 되었습니다.");
      setUser(null);
    },
    onError: (error: any) => {
      if (axios.isAxiosError(error)) {
        const message =
          error.response?.data?.detail || "로그아웃에 실패했습니다.";
        toast.error(`❌ ${message}`);
      } else {
        toast.error("예상치 못한 오류가 발생했습니다.");
      }
    },
  });
}
