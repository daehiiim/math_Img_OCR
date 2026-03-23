import { useEffect } from 'react';
import { FileText } from 'lucide-react';

export default function App() {
  useEffect(() => {
    const observerOptions = {
      root: null,
      rootMargin: '0px',
      threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('active');
        }
      });
    }, observerOptions);

    document.querySelectorAll('.reveal').forEach(el => {
      observer.observe(el);
    });

    const handleScroll = () => {
      const scrolled = window.pageYOffset;
      const glows = document.querySelectorAll('.glow-bg');
      glows.forEach((glow, index) => {
        const speed = 0.05 + (index * 0.01);
        (glow as HTMLElement).style.transform = `translateY(${scrolled * speed}px)`;
      });
    };

    window.addEventListener('scroll', handleScroll);

    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  return (
    <div className="dark font-['Pretendard',sans-serif] selection:bg-white selection:text-black">
      <main>
        {/* Hero Section */}
        <section className="min-h-screen flex flex-col items-center justify-center text-center px-6 relative mb-20">
          <div className="glow-bg" style={{ background: 'radial-gradient(circle at center, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0) 60%)', opacity: 0.1 }}></div>
          <div className="space-y-16 max-w-6xl">
            <h1 className="hero-title text-[5rem] md:text-[9rem] tracking-[-0.05em] leading-[0.95] text-white font-black">
              <span className="hero-word">수학</span>{' '}
              <span className="hero-word">수식을</span>{' '}
              <span className="hero-word">HWPX로,</span><br/>
              <span className="hero-word">완벽한</span>{' '}
              <span className="hero-word">감각으로.</span>
            </h1>
            <div className="flex flex-col items-center gap-10 reveal active" style={{ transitionDelay: '0.6s' }}>
              
              <p className="text-neutral-500 text-[11px] uppercase tracking-[0.6em] leading-loose opacity-60 font-bold">
                <br/>
              </p>
            </div>
          </div>
        </section>

        {/* Main Feature Section */}
        <section className="w-full mb-32 reveal">
          <div className="cosmos-card">
            <div className="glow-bg" style={{ background: 'radial-gradient(circle at center, rgba(255,255,255,0.06) 0%, rgba(0,0,0,0) 80%)' }}></div>
            <div className="relative overflow-hidden bg-neutral-950 border-y border-white/10 group">
              <img 
                alt="디지털 작업 공간" 
                className="w-full h-[512px] object-cover opacity-30 grayscale contrast-125 group-hover:scale-105 transition-transform duration-[3s]" 
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAUbOoVIra_wGGc0Y8fJTDtAOB9SyewR6KJw8YY4wtSdtUGyuuGDuHn189WHLiEKF0DQOAKabwg3dkUTBnFrJZYXKEIZix6MT8pS9aRoEV3kxHqe70hAuaDfhyhVrdfdJ_R-bRa1DE976ej6IJMY4DON08gdbhmeJF3c-jZauCXcfQmB6N96Vz72LIXZ06_8Ad64iZLdDHBRFCnLuPgjyhpateoHa88_Flu2s7X43bR07VocdjO98rKU8l5LxursfAiKrO8pWbVjLE"
              />
              <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                <div className="text-center px-12 max-w-3xl">
                  <h2 className="text-3xl md:text-5xl text-white tracking-[-0.05em] mb-10 uppercase reveal font-black">
                    수학문제 직접 타이핑하느라<br/>힘들지 않았나요?
                  </h2>
                  <p className="text-neutral-300 text-sm md:text-base leading-loose tracking-wide opacity-80 reveal font-medium" style={{ transitionDelay: '0.2s' }}>사진만 찍으면 바로 출력가능한 한글파일로 변환해줍니다.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Three Cards Section */}
        <section className="max-w-[1800px] mx-auto px-10 pb-40">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 items-stretch">
            {/* Card 1 - Source Image */}
            <div className="cosmos-card reveal">
              <div className="glow-bg"></div>
              <div className="relative overflow-hidden bg-neutral-950 border border-white/10 group h-80">
                <img 
                  alt="원본 이미지" 
                  className="w-full h-full object-cover opacity-60 grayscale group-hover:grayscale-0 group-hover:opacity-90 group-hover:scale-105 transition-all duration-[2s]" 
                  src="https://images.unsplash.com/photo-1560785472-2f186f554644?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxoYW5kd3JpdHRlbiUyMG1hdGglMjBwcm9ibGVtJTIwcGFwZXIlMjBzY2FufGVufDF8fHx8MTc3NDIzODAyN3ww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                />
                <div className="absolute top-6 left-6"><span className="text-[9px] uppercase tracking-[0.25em] text-white/50 border border-white/10 px-3 py-1.5 rounded-full backdrop-blur-md font-bold">원본 사진</span></div>
              </div>
              <div className="mt-8 flex-grow">
                <h3 className="text-base tracking-[0.25em] uppercase mb-4 font-black">사진을 올리세요</h3>
                <p className="text-sm text-neutral-500 leading-relaxed tracking-wide font-medium">어떤 필기나 복잡한 인쇄물이라도 원본의 의도를 완벽하게 파악합니다. 수학적 구조를 이해하는 인공지능이 텍스트 이상의 의미를 읽어냅니다.</p>
              </div>
            </div>

            {/* Card 2 - OCR Result */}
            <div className="cosmos-card reveal" style={{ transitionDelay: '0.1s' }}>
              <div className="glow-bg"></div>
              <div className="relative overflow-hidden bg-neutral-950 border border-white/10 group h-80">
                <img 
                  alt="OCR 결과" 
                  className="w-full h-full object-cover opacity-80 group-hover:opacity-100 group-hover:scale-105 transition-all duration-[2s]" 
                  src="https://images.unsplash.com/photo-1711613160734-11caf3ce151d?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxwcmludGVkJTIwbWF0aGVtYXRpY3MlMjB0ZXh0Ym9vayUyMGNsZWFufGVufDF8fHx8MTc3NDIzODAyOHww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                />
                <div className="absolute top-6 left-6"><span className="text-[9px] uppercase tracking-[0.25em] text-white/50 border border-white/10 px-3 py-1.5 rounded-full backdrop-blur-md font-bold">출력 결과</span></div>

              </div>
              <div className="mt-8 flex-grow">
                <h3 className="text-base tracking-[0.25em] uppercase mb-4 font-black">결과를 확인하세요</h3>
                <p className="text-sm text-neutral-500 leading-relaxed tracking-wide font-medium">복잡한 적분이나 분수 등 수식 형태를 hwpx 형식으로 즉각 변환하여 한글에서 편집 가능한 상태로 제공합니다.</p>
              </div>
            </div>

            {/* Card 3 - Output Format */}
            <div className="cosmos-card reveal" style={{ transitionDelay: '0.2s' }}>
              <div className="glow-bg"></div>
              <div className="relative overflow-hidden bg-neutral-950 border border-white/10 group h-80">
                <img 
                  alt="출력 형식" 
                  className="w-full h-full object-cover opacity-70 group-hover:opacity-100 group-hover:scale-105 transition-all duration-[2s]" 
                  src="https://images.unsplash.com/photo-1663177271861-3d622a502fee?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxkb2N1bWVudCUyMGZpbGUlMjBmb3JtYXQlMjBjbGVhbiUyMHdoaXRlJTIwYmFja2dyb3VuZHxlbnwxfHx8fDE3NzQyMzgxMTh8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                />
                <div className="absolute top-6 left-6"><span className="text-[9px] uppercase tracking-[0.25em] text-white/50 border border-white/10 px-3 py-1.5 rounded-full backdrop-blur-md font-bold">무료 이용</span></div>
              </div>
              <div className="mt-8 flex-grow">
                <h3 className="text-base tracking-[0.25em] uppercase mb-4 font-black">무료로 이용하세요</h3>
                <p className="text-sm text-neutral-500 leading-relaxed tracking-wide font-medium">OPEN AI API 키가 있으시다면 본인의 키를 등록해서 무료로 이용하실 수 있습니다.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Call to Action Section */}
        <section className="py-96 border-t border-white/5 relative">
          <div className="glow-bg" style={{ background: 'radial-gradient(circle at center, rgba(255,255,255,0.04) 0%, rgba(0,0,0,0) 70%)', opacity: 0.1 }}></div>
          <div className="max-w-5xl mx-auto px-10 text-center">
            <span className="uppercase tracking-[0.8em] text-neutral-500 block reveal font-bold text-[15px] mx-[0px] mt-[0px] mb-[4px]">사진만 찍으면 끝이니까</span>
            <h2 className="text-4xl md:text-7xl text-white mb-20 tracking-[-0.05em] leading-[1.1] reveal font-black" style={{ transitionDelay: '0.2s' }}>
              당신의 작업 방식을<br/>혁신할 준비가 되셨나요?
            </h2>
            <div className="flex flex-col md:flex-row items-center justify-center gap-8 reveal" style={{ transitionDelay: '0.4s' }}>
              <button className="w-full md:w-auto bg-white text-black px-20 py-6 rounded-full uppercase tracking-[0.25em] hover:bg-neutral-200 transition-all duration-500 active:scale-95 shadow-xl hover:shadow-white/10 font-black text-[20px]">계정 만들기</button>
              <button className="w-full md:w-auto border border-white/10 text-white px-20 py-6 rounded-full text-[20px] uppercase tracking-[0.25em] hover:bg-white hover:text-black transition-all duration-700 active:scale-95 font-black">
                요금제 보기
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="w-full py-32 px-10 bg-black border-t border-white/5 reveal">
        <div className="flex flex-col md:flex-row justify-between items-start gap-16 w-full max-w-[1800px] mx-auto">
          <div className="flex flex-col gap-8">
            <div className="text-base text-white uppercase tracking-[0.25em] font-black">
              Math OCR
            </div>
            <p className="text-[10px] tracking-[0.25em] uppercase text-neutral-600 leading-relaxed font-bold"> <br/></p>
          </div>
          <div className="flex flex-wrap gap-x-16 gap-y-6">
            <a className="text-[10px] tracking-[0.25em] uppercase text-neutral-600 hover:text-white transition-colors duration-500 font-bold" href="#">
              개인정보 처리방침
            </a>
            <a className="text-[10px] tracking-[0.25em] uppercase text-neutral-600 hover:text-white transition-colors duration-500 font-bold" href="#">
              이용약관
            </a>
            
            
          </div>
        </div>
      </footer>
    </div>
  );
}