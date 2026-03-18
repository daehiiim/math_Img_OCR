import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const hasSupabaseAuth = Boolean(supabaseUrl && supabaseAnonKey);

// Supabase 환경값이 있는 경우에만 브라우저 클라이언트를 생성한다.
export const browserSupabase = hasSupabaseAuth
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: true,
      },
    })
  : null;
