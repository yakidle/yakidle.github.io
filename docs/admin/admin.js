'use strict';
const $=id=>document.getElementById(id);
let connected=false, recorder=null, mediaStream=null, chunks=[], recordedFile=null, previewURL=null;
function base(){return ($('apiUrl').value.trim() || window.XIAOYU_CONFIG?.apiBase || (location.hostname.endsWith('github.io')?'':location.origin)).replace(/\/+$/,'')}
function auth(){return {'X-Xiaoyu-Admin':$('adminKey').value.trim()}}
function msg(id,text,error=false){$(id).textContent=text;$(id).classList.toggle('error',error)}
function setConnected(val){connected=val;['uploadStoryBtn','refreshBtn','saveVoiceBtn'].forEach(id=>$(id).disabled=!val)}
async function call(path,opts={}){
  const b=base();if(!b)throw new Error('请填写声音服务的 HTTPS 地址。');
  const headers={...auth(),...(opts.headers||{})};
  const res=await fetch(b+path,{...opts,headers});
  const info=await res.json().catch(()=>({}));
  if(!res.ok)throw new Error(info.error||'请求失败 ('+res.status+')');
  return info;
}
$('apiUrl').value=window.XIAOYU_CONFIG?.apiBase||'';
$('connectBtn').onclick=async()=>{
  if(!$('adminKey').value.trim())return msg('connectStatus','先填写管理员密钥。',true);
  msg('connectStatus','正在检查后台连接…');setConnected(false);
  try{
    const s=await call('/api/admin/status');setConnected(true);
    msg('connectStatus',`连接成功。当前故事 ${s.story_count} 篇；声音样本${s.voice_saved?'已保存':'尚未录入'}。`);
    msg('voiceStatus',s.voice_saved?'已有声音样本，修改后可重新录入。':'还没有保存声音样本。');
    await refresh();
  }catch(e){msg('connectStatus','连接失败：'+e.message,true)}
};
async function refresh(){
  if(!connected)return;
  try{
    const r=await call('/api/stories');const list=$('adminStoryList');list.replaceChildren();
    if(!r.stories.length){list.textContent='还没有故事，录下第一篇吧。';return;}
    for(const s of r.stories){
      const row=document.createElement('div');row.className='item';
      const data=document.createElement('div');const title=document.createElement('strong');title.textContent=s.title;
      const note=document.createElement('div');note.className='note';note.textContent=s.description||s.created_at||'';data.append(title,note);
      const actions=document.createElement('div');actions.className='item-buttons';
      const edit=document.createElement('button');edit.textContent='改信息';edit.onclick=async()=>{
        const name=prompt('修改故事名字：',s.title);if(name===null)return;
        const detail=prompt('修改故事简介：',s.description||'');if(detail===null)return;
        try{await call('/api/admin/stories/'+s.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:name.trim(),description:detail.trim()})});msg('uploadStatus','故事信息修改成功。发布到 GitHub 后公网网站同步。');await refresh()}
        catch(e){msg('uploadStatus','修改失败：'+e.message,true)}
      };
      const del=document.createElement('button');del.textContent='删除';del.className='danger';del.onclick=async()=>{
        if(!confirm('确定删除「'+s.title+'」？对应录音也会从本机故事库中删除，且不能撤销。'))return;
        try{await call('/api/admin/stories/'+s.id,{method:'DELETE'});msg('uploadStatus','已经从本机故事盒子中删除。发布到 GitHub 后公网同步。');await refresh()}
        catch(e){msg('uploadStatus','删除失败：'+e.message,true)}
      };actions.append(edit,del);row.append(data,actions);list.append(row);
    }
  }catch(e){msg('uploadStatus','读取故事列表失败：'+e.message,true)}
}
$('refreshBtn').onclick=refresh;
$('storyFile').addEventListener('change',()=>{
  if($('storyFile').files?.length){recordedFile=null;$('recordedPreview').hidden=true;msg('uploadStatus','已选择本地录音：'+$('storyFile').files[0].name)}
});
$('recordBtn').onclick=async()=>{
  if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder)return msg('uploadStatus','浏览器不支持录音，请直接上传已有 MP3 文件。',true);
  try{
    mediaStream=await navigator.mediaDevices.getUserMedia({audio:true});
    const candidates=['audio/mp4','audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus'];
    const type=candidates.find(t=>MediaRecorder.isTypeSupported(t))||'';
    recorder=new MediaRecorder(mediaStream,type?{mimeType:type}:undefined);
    chunks=[];
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
    recorder.onstop=()=>{
      const mime=recorder.mimeType||type||'audio/webm';
      const ext=mime.includes('mp4')?'m4a':mime.includes('ogg')?'ogg':'webm';
      const blob=new Blob(chunks,{type:mime});
      if(!blob.size)return msg('uploadStatus','录音为空，请重试。',true);
      recordedFile=new File([blob],'小鱼新录的故事.'+ext,{type:mime});
      $('storyFile').value='';
      if(previewURL)URL.revokeObjectURL(previewURL);
      previewURL=URL.createObjectURL(blob);
      $('recordedPreview').src=previewURL;$('recordedPreview').hidden=false;
      msg('uploadStatus','录音已完成，可以试听，满意后点击“保存到故事盒子”。');
      mediaStream?.getTracks().forEach(track=>track.stop());mediaStream=null;
    };
    recorder.start();$('recordBtn').disabled=true;$('stopBtn').disabled=false;msg('uploadStatus','正在录音中，请对着麦克风讲故事…');
  }catch(e){mediaStream?.getTracks().forEach(track=>track.stop());msg('uploadStatus','麦克风无法使用：'+e.message,true)}
};
$('stopBtn').onclick=()=>{if(recorder?.state==='recording')recorder.stop();$('recordBtn').disabled=false;$('stopBtn').disabled=true};
$('uploadStoryBtn').onclick=async()=>{
  const title=$('storyTitle').value.trim();const file=recordedFile||$('storyFile').files?.[0];
  if(!title||!file)return msg('uploadStatus','先填写标题，再上传或录制一段音频。',true);
  const body=new FormData();body.append('title',title);body.append('description',$('storyDesc').value.trim());body.append('audio',file);
  $('uploadStoryBtn').disabled=true;msg('uploadStatus','正在保存故事…');
  try{await call('/api/admin/stories',{method:'POST',body});
    msg('uploadStatus','保存成功！本机可立即播放。记得通过 GitHub Desktop 提交和推送故事库变更，公网才会同步。');
    $('storyTitle').value='';$('storyDesc').value='';$('storyFile').value='';recordedFile=null;$('recordedPreview').hidden=true;await refresh();
  }catch(e){msg('uploadStatus','保存失败：'+e.message,true)}finally{$('uploadStoryBtn').disabled=!connected}
};
$('saveVoiceBtn').onclick=async()=>{
  const file=$('voiceFile').files?.[0];const promptText=$('voicePrompt').value.trim();
  if(!file||!promptText)return msg('voiceStatus','需要声音文件，以及这段录音逐字对应的文字。',true);
  const body=new FormData();body.append('audio',file);body.append('prompt_text',promptText);
  $('saveVoiceBtn').disabled=true;msg('voiceStatus','正在保存声音样本…');
  try{await call('/api/admin/voice',{method:'POST',body});msg('voiceStatus','声音样本保存成功！以后“我想听这个”会使用这段声音。');}
  catch(e){msg('voiceStatus','保存失败：'+e.message,true)}finally{$('saveVoiceBtn').disabled=!connected}
};
