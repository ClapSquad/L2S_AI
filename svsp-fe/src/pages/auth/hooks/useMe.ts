import { useQuery } from "@tanstack/react-query";
import { axiosInstance } from "src/apis/axiosInstance";
import { API } from "src/apis/endpoints";

export interface UserInfoResponse {
  user: {
    email: string;
    username: string;
  };
}

export function useMe() {
  return useQuery<UserInfoResponse, Error>({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await axiosInstance.get(API.AUTH.ME);
      return res.data;
    },
  });
}
