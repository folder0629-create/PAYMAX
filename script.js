// 최근 상담 현황: 당일/전일 날짜 자동 생성 + 끊김 없는 세로 롤링
const pad=n=>String(n).padStart(2,"0");
const fmt=d=>`${d.getFullYear()}.${pad(d.getMonth()+1)}.${pad(d.getDate())}`;
const today=new Date();
const yesterday=new Date(today); yesterday.setDate(today.getDate()-1);

const rows=[
 [fmt(today),"예식장","박*지","상담 중","active"],
 [fmt(today),"일반음식점","황*윤","상담 대기","wait"],
 [fmt(today),"카페·디저트","권*연","상담 대기","wait"],
 [fmt(today),"소매점","김*영","상담 완료","done"],
 [fmt(yesterday),"약국","송*진","상담 완료","done"],
 [fmt(yesterday),"치과","최*호","상담 대기","wait"],
 [fmt(yesterday),"카페·디저트","남*후","상담 중","active"],
 [fmt(yesterday),"뷰티·피부관리","안*호","상담 대기","wait"]
];

const box=document.getElementById("rolling");
if(box){
  const track=document.createElement("div");
  track.className="rollingTrack";
  [...rows,...rows].forEach(r=>{
    const d=document.createElement("div");
    d.className="statusRow";
    d.innerHTML=`<span>${r[0]}</span><b>${r[1]}</b><span>${r[2]}</span><span class="badge ${r[4]}">${r[3]}</span>`;
    track.appendChild(d);
  });
  box.innerHTML="";
  box.appendChild(track);
}

// 기존 업종 자동 슬라이드 유지
const industry=document.getElementById("industryTrack");
let x=0;
if(industry){
 setInterval(()=>{
   x+=164;
   if(x>industry.scrollWidth-industry.clientWidth)x=0;
   industry.scrollTo({left:x,behavior:"smooth"});
 },2200);
}

// 기존 상담폼 동작 유지
const form=document.getElementById("consultForm");
if(form){
 form.addEventListener("submit",e=>{
   e.preventDefault();
   alert("현재는 디자인용 폼입니다. 서버 API/DB 연결 후 실제 접수가 가능합니다.");
 });
}

// FIX: 모바일 5단계 절차 자동 좌측 슬라이드
(function(){
  const slider = document.querySelector(".steps");
  if(!slider) return;

  const cards = Array.from(slider.querySelectorAll("article"));
  if(cards.length < 2) return;

  let idx = 0;
  let timer = null;

  function isMobile(){
    return window.matchMedia("(max-width: 850px)").matches;
  }

  function moveToCard(index){
    if(!isMobile()) return;
    const card = cards[index];
    const left = card.offsetLeft - slider.offsetLeft - (slider.clientWidth - card.clientWidth)/2;
    slider.scrollTo({left: Math.max(0,left), behavior:"smooth"});
  }

  function start(){
    stop();
    if(!isMobile()) return;
    timer = setInterval(function(){
      idx = (idx + 1) % cards.length;
      moveToCard(idx);
    }, 2300);
  }

  function stop(){
    if(timer){ clearInterval(timer); timer=null; }
  }

  // 사용자가 직접 넘기는 동안 잠깐 멈춘 뒤 다시 자동 진행
  slider.addEventListener("touchstart", stop, {passive:true});
  slider.addEventListener("touchend", function(){ setTimeout(start,1200); }, {passive:true});
  window.addEventListener("resize", start);

  // DOM/레이아웃 완료 후 시작
  if(document.readyState === "complete"){
    setTimeout(start,500);
  } else {
    window.addEventListener("load", function(){ setTimeout(start,500); });
  }
})();
