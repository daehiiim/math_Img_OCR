import { useState, useRef, useCallback, useEffect } from "react";
import { useLocation, useNavigate } from "react-router";
import { useJobs } from "../context/JobContext";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Card, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import { Upload, ImageIcon, ArrowRight } from "lucide-react";
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
import { PageIntro } from "./shared/PageIntro";
import { ExecutionOptionsPanel } from "./shared/ExecutionOptionsPanel";
import { RegionWorkspaceShell } from "./shared/RegionWorkspaceShell";

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

  /** 선택한 파일과 draft 편집 상태를 초기화한다. */
  const resetDraftSelection = useCallback(() => {
    setPreview(null);
    setRegions([]);
    setExecutionOptions(defaultExecutionOptions);
    setErrorMessage(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  /** 같은 파일도 다시 고를 수 있도록 파일 선택기를 연다. */
  const openFilePicker = useCallback(() => {
    if (!fileInputRef.current) {
      return;
    }

    fileInputRef.current.value = "";
    fileInputRef.current.click();
  }, []);

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
    <div className="mx-auto max-w-[1480px] p-4 sm:p-6 lg:p-8">
      <input
        ref={fileInputRef}
        type="file"
        accept=".png,.jpg,.jpeg"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            handleFile(file);
          }
        }}
      />

      <PageIntro
        title="수식 이미지 변환 작업 시작"
        description="PNG, JPG, JPEG 이미지를 올리고 필요한 문제 영역만 선택한 뒤 수식 OCR과 HWPX workflow를 시작합니다."
      />

      {/* 업로드 영역 */}
      {!preview ? (
        <Card className="mx-auto mb-6 max-w-4xl">
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
                onClick={openFilePicker}
                className="gap-2"
              >
                <ImageIcon className="w-4 h-4" />
                파일 선택
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="min-w-0">
            <RegionWorkspaceShell
              title="영역 지정"
              description="이미지 위에 필요한 문제 영역만 선택하고 draft 상태를 그대로 유지합니다."
              fileName={preview.name}
              imageMeta={`${preview.width} × ${preview.height}px`}
              regionCount={regions.length}
              error={errorMessage}
              onReset={resetDraftSelection}
            >
                <RegionEditor
                  imageUrl={preview.url}
                  imageWidth={preview.width}
                  imageHeight={preview.height}
                  regions={regions}
                  onRegionsChange={setRegions}
                  disabled={isSubmitting}
                  onSaveRegions={async (draftRegions) => {
                    setRegions(draftRegions);
                    toast.success("영역 draft가 반영되었습니다.");
                  }}
                />
            </RegionWorkspaceShell>
          </div>

          <div className="space-y-6 xl:sticky xl:top-6">
            <ExecutionOptionsPanel
              title="파이프라인 실행"
              description="원하는 작업만 선택해서 실행할 수 있습니다."
              options={[
                {
                  id: "draft-do-ocr",
                  key: "doOcr",
                  label: "문제 타이핑",
                  description: "OCR과 수식 추출을 실행합니다.",
                },
                {
                  id: "draft-do-image-stylize",
                  key: "doImageStylize",
                  label: "이미지 생성",
                  description: "도형·그림을 생성합니다.",
                },
                {
                  id: "draft-do-explanation",
                  key: "doExplanation",
                  label: "해설 작성",
                  description: "영역별 풀이 해설을 생성합니다.",
                },
              ]}
              values={executionOptions}
              requiredCredits={requiredCredits}
              summary="현재 편집 중인 draft 영역 기준 예상 차감입니다."
              actionLabel={isSubmitting ? "파이프라인 실행 중..." : "파이프라인 실행"}
              actionIcon={<ArrowRight data-icon="inline-end" />}
              actionDisabled={isSubmitting}
              onToggle={updateExecutionOption}
              onAction={() => void handleRunPipeline()}
            />
          </div>
        </div>
      )}
    </div>
  );
}
