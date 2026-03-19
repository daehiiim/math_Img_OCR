import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router";
import { useJobs } from "../context/JobContext";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Upload, ImageIcon, ArrowRight, X } from "lucide-react";
import { resolveUploadGate } from "../lib/authFlow";
import { validateImageFile } from "../lib/uploadPreview";

export function NewJobPage() {
  const { createJob } = useJobs();
  const { isAuthenticated, prepareLogin, user } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [preview, setPreview] = useState<{
    url: string;
    name: string;
    width: number;
    height: number;
    file: File;
  } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const ensureUploadAccess = useCallback(() => {
    const decision = resolveUploadGate({
      isAuthenticated,
      openAiConnected: user?.openAiConnected ?? false,
      credits: user?.credits ?? 0,
    });

    if (decision === "login") {
      prepareLogin("/new");
      toast("로그인이 필요합니다", {
        description: "이미지를 올리려면 먼저 Google 로그인을 진행해주세요.",
      });
      navigate("/login");
      return false;
    }

    if (decision === "connect-openai") {
      toast("먼저 OpenAI 연결 또는 크레딧이 필요합니다", {
        description: "로그인 후에는 OpenAI API key 연결을 먼저 안내합니다.",
      });
      navigate("/connect-openai");
      return false;
    }

    return true;
  }, [isAuthenticated, navigate, prepareLogin, user?.credits, user?.openAiConnected]);

  const handleFile = useCallback((file: File) => {
    const validationError = validateImageFile(file);
    if (validationError) {
      toast.error(validationError);
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const url = e.target?.result as string;
      const img = new Image();
      img.onload = () => {
        setPreview({ url, name: file.name, width: img.width, height: img.height, file });
        setErrorMessage(null);
      };
      img.src = url;
    };
    reader.readAsDataURL(file);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      if (!ensureUploadAccess()) {
        return;
      }
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith("image/")) {
        handleFile(file);
      }
    },
    [ensureUploadAccess, handleFile]
  );

  const handleCreateJob = async () => {
    if (!preview || isSubmitting) return;

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const jobId = await createJob(
        preview.name,
        preview.url,
        preview.width,
        preview.height,
        preview.file
      );
      navigate(`/workspace/job/${jobId}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "작업 생성 중 오류가 발생했습니다.";
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1>새 작업 생성</h1>
        <p className="text-muted-foreground text-[14px] mt-1">
          공개 페이지에서 이미지를 검토하고, 실제 업로드 시점에만 로그인/연결을 요구합니다.
        </p>
      </div>

      {/* 업로드 영역 */}
      {!preview ? (
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div
              className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
                dragActive
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
            >
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
                <Upload className="w-7 h-7 text-muted-foreground" />
              </div>
              <h3 className="text-[15px] mb-1">이미지를 드래그하거나 클릭하여 업로드</h3>
              <p className="text-[13px] text-muted-foreground mb-4">
                PNG, JPG, JPEG 형식 지원 · 10MB 이하
              </p>
              <Button
                variant="outline"
                onClick={() => {
                  if (!ensureUploadAccess()) {
                    return;
                  }

                  fileInputRef.current?.click();
                }}
                className="gap-2"
              >
                <ImageIcon className="w-4 h-4" />
                파일 선택
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".png,.jpg,.jpeg"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
              />
            </div>
          </CardContent>
        </Card>
      ) : (
        /* 미리보기 */
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-[14px]">업로드 미리보기</CardTitle>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  setPreview(null);
                  setErrorMessage(null);
                }}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="bg-muted rounded-xl overflow-hidden mb-4">
              <img
                src={preview.url}
                alt={preview.name}
                className="w-full max-h-[400px] object-contain"
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[14px]">{preview.name}</p>
                <p className="text-[12px] text-muted-foreground">
                  {preview.width} × {preview.height}px
                </p>
              </div>
              <Button onClick={() => void handleCreateJob()} className="gap-2" disabled={isSubmitting}>
                {isSubmitting ? "작업 생성 중..." : "작업 생성 및 영역 지정"}
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
            {errorMessage && (
              <p className="text-[12px] text-destructive mt-3">{errorMessage}</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
