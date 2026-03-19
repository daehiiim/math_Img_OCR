import { useState, useRef, useCallback, useEffect } from "react";
import { useLocation, useNavigate } from "react-router";
import { useJobs } from "../context/JobContext";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Upload, ImageIcon, ArrowRight, Sparkles, X } from "lucide-react";
import { resolveUploadGate } from "../lib/authFlow";
import { calculateRequiredCredits } from "../lib/executionCredits";
import {
  clearGuestDraft,
  readGuestDraft,
  saveGuestDraft,
} from "../lib/guestDraftStorage";
import { validateImageFile } from "../lib/uploadPreview";
import type { JobExecutionOptions, Region } from "../store/jobStore";
import { RegionEditor } from "./RegionEditor";
import { Checkbox } from "./ui/checkbox";
import { Label } from "./ui/label";

const defaultExecutionOptions: JobExecutionOptions = {
  doOcr: true,
  doImageStylize: true,
  doExplanation: true,
};

const draftResumePath = "/new?resumeDraft=1";
const pricingResumePath = `/pricing?returnTo=${encodeURIComponent(draftResumePath)}`;

export function NewJobPage() {
  const location = useLocation();
  const { createJob, runPipeline, saveRegions } = useJobs();
  const { isAuthenticated, prepareLogin, refreshProfile, user } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [preview, setPreview] = useState<{
    url: string;
    name: string;
    mimeType: string;
    width: number;
    height: number;
    file: File;
  } | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);
  const [executionOptions, setExecutionOptions] = useState<JobExecutionOptions>(defaultExecutionOptions);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const hasSelectedAction =
    executionOptions.doOcr || executionOptions.doImageStylize || executionOptions.doExplanation;
  const requiredCredits = calculateRequiredCredits(
    executionOptions,
    Boolean(user?.openAiConnected),
    regions
  );

  useEffect(() => {
    let cancelled = false;

    if (!new URLSearchParams(location.search).has("resumeDraft")) {
      return () => {
        cancelled = true;
      };
    }

    const restoreGuestDraft = async () => {
      const draft = await readGuestDraft();
      if (!draft || cancelled) {
        return;
      }

      setPreview({
        url: draft.image.url,
        name: draft.image.name,
        mimeType: draft.image.mimeType,
        width: draft.image.width,
        height: draft.image.height,
        file: draft.image.file,
      });
      setRegions(draft.regions);
      setExecutionOptions(draft.executionOptions);
      setErrorMessage(null);
    };

    void restoreGuestDraft();

    return () => {
      cancelled = true;
    };
  }, [location.search]);

  useEffect(() => {
    return () => {
      if (preview?.url.startsWith("blob:")) {
        URL.revokeObjectURL(preview.url);
      }
    };
  }, [preview]);

  /** 현재 공개 draft를 브라우저 저장소에 안전하게 저장한다. */
  const persistGuestDraft = useCallback(async () => {
    if (!preview) {
      return true;
    }

    try {
      await saveGuestDraft({
        image: {
          file: preview.file,
          name: preview.name,
          mimeType: preview.mimeType,
          width: preview.width,
          height: preview.height,
        },
        executionOptions,
        regions,
      });
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : "공개 draft 저장에 실패했습니다.";
      toast.error(message);
      return false;
    }
  }, [executionOptions, preview, regions]);

  /** 실제 실행 전에 로그인 또는 자원 게이트를 확인한다. */
  const ensureExecutionAccess = useCallback(async () => {
    const decision = resolveUploadGate({
      isAuthenticated,
      openAiConnected: user?.openAiConnected ?? false,
      credits: user?.credits ?? 0,
    });

    if (decision === "login") {
      const saved = await persistGuestDraft();
      if (!saved) {
        return false;
      }

      prepareLogin(draftResumePath);
      toast("로그인이 필요합니다", {
        description: "파이프라인 실행 전에 Google 로그인을 진행해주세요.",
      });
      navigate("/login");
      return false;
    }

    if (decision === "connect-openai") {
      const saved = await persistGuestDraft();
      if (!saved) {
        return false;
      }

      toast("먼저 OpenAI 연결 또는 크레딧이 필요합니다", {
        description: "실행 전에 OpenAI 연결 또는 크레딧 구매를 완료해주세요.",
      });
      navigate(`/connect-openai?returnTo=${encodeURIComponent(draftResumePath)}`);
      return false;
    }

    return true;
  }, [
    isAuthenticated,
    navigate,
    persistGuestDraft,
    prepareLogin,
    user?.credits,
    user?.openAiConnected,
  ]);

  /** 부족한 자원을 보충할 다음 경로를 계산해 이동한다. */
  const redirectForInsufficientCredits = useCallback(async () => {
    const currentCredits = user?.credits ?? 0;
    const requiredCreditsWithOpenAi = calculateRequiredCredits(executionOptions, true, regions);
    const saved = await persistGuestDraft();

    if (!saved) {
      return;
    }

    if (!user?.openAiConnected && currentCredits >= requiredCreditsWithOpenAi) {
      toast("OpenAI 연결로 바로 실행할 수 있습니다", {
        description: "OCR과 해설 차감은 OpenAI key 연결로 줄일 수 있습니다.",
      });
      navigate(`/connect-openai?returnTo=${encodeURIComponent(draftResumePath)}`);
      return;
    }

    toast("선택한 작업을 실행하기 위한 크레딧이 부족합니다.", {
      description: "결제 후 현재 draft로 다시 돌아와 이어서 실행할 수 있습니다.",
    });
    navigate(pricingResumePath);
  }, [executionOptions, navigate, persistGuestDraft, regions, user?.credits, user?.openAiConnected]);

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
        setPreview({
          url,
          name: file.name,
          mimeType: file.type,
          width: img.width,
          height: img.height,
          file,
        });
        setRegions([]);
        setExecutionOptions(defaultExecutionOptions);
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
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith("image/")) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  /** 실행 옵션 체크 상태를 변경한다. */
  const updateExecutionOption = useCallback((key: keyof JobExecutionOptions, checked: boolean) => {
    setExecutionOptions((prev) => ({
      ...prev,
      [key]: checked,
    }));
  }, []);

  const handleRunPipeline = async () => {
    if (!preview || isSubmitting) return;
    if (regions.length === 0) {
      toast.error("먼저 영역을 지정하세요.");
      return;
    }
    if (!hasSelectedAction) {
      toast.error("실행할 작업을 하나 이상 선택하세요.");
      return;
    }
    if (!(await ensureExecutionAccess())) {
      return;
    }
    if ((user?.credits ?? 0) < requiredCredits) {
      await redirectForInsufficientCredits();
      return;
    }

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
      await saveRegions(jobId, regions);
      await runPipeline(jobId, executionOptions);
      await refreshProfile();
      await clearGuestDraft();
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
          파일 선택과 영역 지정은 로그인 없이 진행하고, 파이프라인 실행 직전에만 로그인합니다.
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
                onClick={() => fileInputRef.current?.click()}
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
            </div>
            {errorMessage && (
              <p className="text-[12px] text-destructive mt-3">{errorMessage}</p>
            )}
          </CardContent>
        </Card>
      )}

      {preview ? (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-[14px]">영역 지정</CardTitle>
              </CardHeader>
              <CardContent>
                <RegionEditor
                  imageUrl={preview.url}
                  imageWidth={preview.width}
                  imageHeight={preview.height}
                  regions={regions}
                  onRegionsChange={setRegions}
                  onSaveRegions={async (draftRegions) => {
                    setRegions(draftRegions);
                    toast.success("영역 draft가 반영되었습니다.");
                  }}
                />
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-[14px] flex items-center gap-2">
                  <Sparkles className="w-4 h-4" />
                  파이프라인 실행
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  {[
                    {
                      id: "draft-do-ocr",
                      key: "doOcr" as const,
                      label: "문제 타이핑",
                      description: "OCR과 수식 추출을 실행합니다.",
                    },
                    {
                      id: "draft-do-image-stylize",
                      key: "doImageStylize" as const,
                      label: "이미지 생성",
                      description: "도형·그림을 생성합니다.",
                    },
                    {
                      id: "draft-do-explanation",
                      key: "doExplanation" as const,
                      label: "해설 작성",
                      description: "영역별 풀이 해설을 생성합니다.",
                    },
                  ].map((option) => (
                    <div key={option.id} className="rounded-xl border p-3">
                      <div className="flex items-start gap-3">
                        <Checkbox
                          id={option.id}
                          checked={executionOptions[option.key]}
                          onCheckedChange={(checked) => updateExecutionOption(option.key, checked === true)}
                          aria-label={option.label}
                        />
                        <div className="flex-1 space-y-1">
                          <Label htmlFor={option.id}>{option.label}</Label>
                          <p className="text-[12px] text-muted-foreground">{option.description}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rounded-xl bg-muted/40 p-3 text-[12px]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-muted-foreground">이번 실행 최대 차감 예정</span>
                    <span className="font-semibold text-foreground">{requiredCredits} 크레딧</span>
                  </div>
                  <p className="mt-1 text-muted-foreground">
                    현재 편집 중인 draft 영역 기준 예상 차감입니다.
                  </p>
                </div>

                <Button
                  onClick={() => void handleRunPipeline()}
                  className="w-full gap-2"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "파이프라인 실행 중..." : "파이프라인 실행"}
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : null}
    </div>
  );
}
