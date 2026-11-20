'use strict';
const $ = id => document.getElementById(id);
let stories = [], selected = null, generatedUrl = null;
const API_PREF = 'xiaoyu_api_url';
function apiBase(){
  const saved = localStorage.getItem(API_PREF) || '';
  const cfg = window.XIAOYU_CONFIG?.apiBase || '';
  return (saved || cfg || (location.hostname.endsWith('github.io') ? '' : location.origin)).replace(/\/+$/, '');
}
function say(id, msg, error=false){$(id).textContent=msg; $(id).classList.toggle('error',error);}
function show(mode){
  $('libraryMode').hidden=mode!=='library';$('aiMode').hidden=mode!=='ai';
  $('tabLibrary').classList.toggle('active',mode==='library');$('tabAI').classList.toggle('active',mode==='ai');
  $('tabLibrary').setAttribute('aria-selected',String(mode==='library'));$('tabAI').setAttribute('aria-selected',String(mode==='ai'));
  if(mode==='ai')$('storyAudio').pause();else $('resultAudio').pause();
}
$('tabLibrary').onclick=()=>show('library');$('tabAI').onclick=()=>show('ai');
const plain = (s,defaultText='')=>typeof s==='string'&&s.trim()?s.trim():defaultText;
async function loadStories(){
  try{
    const resp=await fetch('../story-archive/catalog.json',{cache:'no-store'});
    if(!resp.ok)throw new Error('故事库暂时不可用');
    const result=await resp.json();
    stories=Array.isArray(result.stories)?result.stories.filter(x=>x&&typeof x.id==='string'&&typeof x.audio==='string'):[];
    renderStories();
  }catch(e){say('libraryStatus',`无法读取故事列表：${e.message}`,true);$('storyCards').textContent='故事盒子暂时打不开。';}
}
function renderStories(){
  const list=$('storyCards');list.replaceChildren();
  if(!stories.length){
    const item=document.createElement('div');item.className='empty';item.textContent='故事盒子还是空的。等小鱼录好第一篇故事，就会出现在这里。';list.append(item);
    $('randomBtn').disabled=true;$('nextRandom').disabled=true;return;
  }
  $('randomBtn').disabled=false;$('nextRandom').disabled=false;
  stories.forEach((story,index)=>{
    const card=document.createElement('button');card.className='story-card'+(selected?.id===story.id?' active':'');card.type='button';
    const icon=document.createElement('span');icon.className='story-icon';icon.textContent=['📖','🌷','⭐','🍀','🐟'][index%5];
    const content=document.createElement('span');content.className='content';
    const strong=document.createElement('strong');strong.textContent=plain(story.title,'未命名故事');
    const small=document.createElement('small');small.textContent=plain(story.description,`小鱼录于 ${plain(story.created_at,'某一天')}`);
    content.append(strong,small);
    const play=document.createElement('span');play.className='play-small';play.textContent='▶';
    card.append(icon,content,play);card.onclick=()=>playStory(story);list.append(card);
  });
  say('libraryStatus',`故事盒子里共有 ${stories.length} 篇故事。`);
}
function playStory(story){
  selected=story;
  const filename=story.audio.replace(/^\.\.\//,'');
  if(!/^story-archive\/audio\/[a-f0-9]{16}\.(mp3|wav|m4a|ogg|webm|flac)$/.test(filename)){
    say('libraryStatus','音频地址有误，无法播放。',true);return;
  }
  const url=new URL('../'+filename,location.href);
  $('storyAudio').src=url.href;
  $('playerTitle').textContent=plain(story.title,'未命名故事');
  $('playerDesc').textContent=plain(story.description,'你喜欢的话，就多听几遍吧。');
  renderStories();
  $('storyAudio').play().catch(()=>say('libraryStatus','浏览器阻止了自动播放，请点击播放器的播放键。'));
}
function randomStory(){
  if(!stories.length)return;
  const choices=stories.length>1?stories.filter(s=>s.id!==selected?.id):stories;
  playStory(choices[Math.floor(Math.random()*choices.length)]);
}
$('randomBtn').onclick=randomStory;$('nextRandom').onclick=randomStory;
$('storyText').addEventListener('input',()=>{$('charCount').textContent=String($('storyText').value.length)});
$('apiUrl').value=localStorage.getItem(API_PREF)||window.XIAOYU_CONFIG?.apiBase||'';
$('saveApi').onclick=()=>{
  const url=$('apiUrl').value.trim().replace(/\/+$/,'');
  if(url && !/^https:\/\/[\w.-]+(?::\d+)?$/.test(url) && !/^http:\/\/127\.0\.0\.1:\d+$/.test(url)){
    say('aiStatus','请输入有效的 HTTPS 地址（本地允许 127.0.0.1）。',true);return;
  }
  if(url)localStorage.setItem(API_PREF,url);else localStorage.removeItem(API_PREF);
  say('aiStatus','连接地址已保存在当前浏览器。');
};
$('generateBtn').onclick=async()=>{
  const text=$('storyText').value.trim();const key=$('listenerKey').value.trim();const base=apiBase();
  if(!text)return say('aiStatus','先写一点想听的文字吧。',true);
  if(!key)return say('aiStatus','请先填写小鱼给你的听故事暗号。',true);
  if(!base)return say('aiStatus','还没配置公网声音服务地址，请展开下方连接设置。',true);
  $('generateBtn').disabled=true;$('generateBtn').textContent='正在合成中…';say('aiStatus','小鱼正在准备故事。稍长的文章可能需要多一点时间。');
  try{
    const res=await fetch(base+'/api/tts',{
      method:'POST',headers:{'Content-Type':'application/json','X-Xiaoyu-Listener':key},
      body:JSON.stringify({text,speed:Number($('speedSelect').value)}),
    });
    if(!res.ok){let info={};try{info=await res.json()}catch{}throw new Error(info.error||`请求失败 (${res.status})`)}
    const wav=await res.blob();
    if(!wav.size||!wav.type.includes('audio'))throw new Error('没有收到正常的音频内容');
    if(generatedUrl)URL.revokeObjectURL(generatedUrl);
    generatedUrl=URL.createObjectURL(wav);
    $('resultAudio').src=generatedUrl;$('downloadWav').href=generatedUrl;
    $('resultEmpty').hidden=true;$('resultReady').hidden=false;
    say('aiStatus','好啦，故事已经读好了 ♡');
    $('resultAudio').play().catch(()=>{});
  }catch(e){say('aiStatus',`暂时没能读出来：${e.message}`,true)}
  finally{$('generateBtn').disabled=false;$('generateBtn').textContent='▶ 小鱼，读给我听'}
};
loadStories();
