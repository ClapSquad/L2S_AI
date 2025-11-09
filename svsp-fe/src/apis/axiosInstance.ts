// base.tsx
import axios, { AxiosError } from "axios";

export const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_API_URL,
  timeout: 3000,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

export const handleApiError = (error: any): never => {
  if (error instanceof AxiosError) {
    throw new Error(
      `API 에러: ${error.response?.data.message || error.message}`
    );
  }
  throw error;
};
