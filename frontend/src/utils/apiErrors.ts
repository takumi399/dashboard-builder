import axios from 'axios';

export const apiErrorMessage = (error: unknown, fallback: string): string => {
  if (!axios.isAxiosError(error)) return fallback;

  const data: unknown = error.response?.data;
  if (typeof data !== 'object' || data === null || !('detail' in data)) return fallback;
  return typeof data.detail === 'string' ? data.detail : fallback;
};

export const isFormValidationError = (error: unknown): error is { errorFields: unknown[] } =>
  typeof error === 'object'
  && error !== null
  && 'errorFields' in error
  && Array.isArray(error.errorFields);
