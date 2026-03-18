declare const __MATH_OCR_VITE_API_BASE__: string;
declare const __MATH_OCR_PUBLIC_APP_URL__: string;

interface ImportMetaEnv {
  readonly VITE_LOCAL_UI_MOCK?: string;
  readonly VITE_LOCAL_UI_MOCK_PAYMENT_OUTCOME?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
