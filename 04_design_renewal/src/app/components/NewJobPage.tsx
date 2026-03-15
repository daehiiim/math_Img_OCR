import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router";
import { useJobs } from "../context/JobContext";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import {
  Upload,
  ImageIcon,
  FileImage,
  ArrowRight,
  X,
  Info,
} from "lucide-react";

// Sample demo images for quick testing
const DEMO_IMAGES = [
  {
    name: "이차방정식 풀이.png",
    url: "data:image/svg+xml;charset=utf-8," +
      encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" fill="#fff">
        <rect width="800" height="500" fill="#f8f9fa"/>
        <rect x="40" y="30" width="720" height="440" rx="8" fill="#fff" stroke="#dee2e6" stroke-width="1"/>
        <text x="60" y="70" font-family="serif" font-size="22" fill="#212529">1. 다음 이차방정식의 근을 구하시오.</text>
        <text x="100" y="130" font-family="serif" font-size="28" fill="#212529">x² - 5x + 6 = 0</text>
        <text x="60" y="200" font-family="serif" font-size="18" fill="#495057">[풀이]</text>
        <text x="80" y="240" font-family="serif" font-size="20" fill="#495057">(x - 2)(x - 3) = 0</text>
        <text x="80" y="280" font-family="serif" font-size="20" fill="#495057">x = 2 또는 x = 3</text>
        <line x1="400" y1="320" x2="400" y2="320" stroke="#dee2e6"/>
        <text x="60" y="350" font-family="serif" font-size="22" fill="#212529">2. 삼각형 ABC에서 넓이를 구하시오.</text>
        <polygon points="200,450 350,380 500,450" fill="none" stroke="#212529" stroke-width="2"/>
        <text x="180" y="468" font-family="serif" font-size="14" fill="#212529">A</text>
        <text x="340" y="375" font-family="serif" font-size="14" fill="#212529">B</text>
        <text x="505" y="468" font-family="serif" font-size="14" fill="#212529">C</text>
        <text x="250" y="415" font-family="serif" font-size="14" fill="#6c757d">5cm</text>
        <text x="410" y="415" font-family="serif" font-size="14" fill="#6c757d">4cm</text>
        <text x="350" y="460" font-family="serif" font-size="14" fill="#6c757d">3cm</text>
      </svg>`),
    width: 800,
    height: 500,
  },
  {
    name: "기하학 문제.png",
    url: "data:image/svg+xml;charset=utf-8," +
      encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" fill="#fff">
        <rect width="800" height="500" fill="#f8f9fa"/>
        <rect x="40" y="30" width="720" height="440" rx="8" fill="#fff" stroke="#dee2e6" stroke-width="1"/>
        <text x="60" y="70" font-family="serif" font-size="22" fill="#212529">3. 원의 넓이를 구하시오. (r = 5cm)</text>
        <circle cx="350" cy="200" r="80" fill="none" stroke="#212529" stroke-width="2"/>
        <line x1="350" y1="200" x2="430" y2="200" stroke="#e74c3c" stroke-width="2" stroke-dasharray="5,5"/>
        <text x="370" y="195" font-family="serif" font-size="14" fill="#e74c3c">r = 5</text>
        <text x="345" y="205" font-family="serif" font-size="12" fill="#212529">O</text>
        <text x="60" y="340" font-family="serif" font-size="22" fill="#212529">4. 피타고라스 정리를 증명하시오.</text>
        <polygon points="100,450 250,450 250,380" fill="none" stroke="#212529" stroke-width="2"/>
        <text x="90" y="468" font-family="serif" font-size="14" fill="#212529">A</text>
        <text x="255" y="468" font-family="serif" font-size="14" fill="#212529">B</text>
        <text x="255" y="375" font-family="serif" font-size="14" fill="#212529">C</text>
        <text x="165" y="468" font-family="serif" font-size="14" fill="#6c757d">a</text>
        <text x="258" y="418" font-family="serif" font-size="14" fill="#6c757d">b</text>
        <text x="155" y="418" font-family="serif" font-size="14" fill="#6c757d">c</text>
        <text x="400" y="420" font-family="serif" font-size="20" fill="#212529">a² + b² = c²</text>
      </svg>`),
    width: 800,
    height: 500,
  },
];

export function NewJobPage() {
  const { createJob } = useJobs();
  const { consumeCredit } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [preview, setPreview] = useState<{
    url: string;
    name: string;
    width: number;
    height: number;
  } | null>(null);

  const handleFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const url = e.target?.result as string;
      const img = new Image();
      img.onload = () => {
        setPreview({ url, name: file.name, width: img.width, height: img.height });
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

  const handleDemoSelect = (demo: (typeof DEMO_IMAGES)[0]) => {
    setPreview({ url: demo.url, name: demo.name, width: demo.width, height: demo.height });
  };

  const handleCreateJob = () => {
    if (!preview) return;
    const jobId = createJob(preview.name, preview.url, preview.width, preview.height);
    navigate(`/job/${jobId}`);
  };

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1>새 작업 생성</h1>
        <p className="text-muted-foreground text-[14px] mt-1">
          수학 문제 이미지를 업로드하여 자동 인식을 시작합니다.
        </p>
      </div>

      {/* Upload Area */}
      {!preview ? (
        <>
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
                  PNG, JPG, BMP 형식 지원 — 수학 시험지/문제 이미지 권장
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
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFile(file);
                  }}
                />
              </div>
            </CardContent>
          </Card>

          {/* Demo Images */}
          <Card>
            <CardHeader>
              <CardTitle className="text-[14px] flex items-center gap-2">
                <Info className="w-4 h-4" />
                데모 이미지 (빠른 테스트)
              </CardTitle>
              <CardDescription>
                이미지가 없다면 아래 샘플 이미지로 파이프라인을 테스트할 수 있습니다.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {DEMO_IMAGES.map((demo) => (
                  <button
                    key={demo.name}
                    onClick={() => handleDemoSelect(demo)}
                    className="text-left border rounded-xl p-3 hover:border-primary/50 hover:bg-accent/30 transition-colors group"
                  >
                    <div className="bg-muted rounded-lg overflow-hidden mb-3 aspect-[8/5]">
                      <img
                        src={demo.url}
                        alt={demo.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileImage className="w-4 h-4 text-muted-foreground" />
                        <span className="text-[13px]">{demo.name}</span>
                      </div>
                      <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        /* Preview */
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-[14px]">업로드 미리보기</CardTitle>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setPreview(null)}
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
              <Button onClick={handleCreateJob} className="gap-2">
                작업 생성 및 영역 지정
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}