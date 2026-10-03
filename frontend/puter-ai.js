/* frontend/puter-ai.js — ZERO-KEY browser AI via Puter.js.
 * User-pays model: usage is billed to the signed-in Puter account. No API key
 * is stored here. Model ids are resolved at runtime against Puter's catalogue.
 * VALIDATION ONLY: never invent a strike, entry, stop-loss or target.
 */
window.PuterAI = (function () {
  const LAYERS = [
    {id:"L1",name:"GPT-5.6 Luna",env:"gpt-5.6-luna",role:"data collection / candidate analysis",web:true},
    {id:"L2",name:"Claude Sonnet 4.6",env:"claude-sonnet-4.6",role:"data verification",web:false},
    {id:"L3",name:"GPT-5.6 Sol",env:"gpt-5.6-sol",role:"independent validation",web:true},
    {id:"L4",name:"DeepSeek Chat",env:"deepseek-chat",role:"quantitative / OI audit",web:false},
    {id:"L5",name:"Gemini 2.5 Flash",env:"gemini-2.5-flash",role:"market structure analysis",web:true},
    {id:"L6",name:"Grok 4",env:"grok-4",role:"final risk audit / cross verification",web:false}
  ];
  const FORBIDDEN=["strike","entry","stop_loss","sl","target","targets","take_profit","tp","position_size","quantity"];
  const VERDICTS=["CALL BUY","PUT BUY","WAIT","NO QUALIFYING TRADE"];

  function available(){return typeof puter!=="undefined"&&!!puter.ai;}
  async function listModels(){try{return await puter.ai.listModels();}catch(e){console.warn("PuterAI.listModels",e);return [];}}
  async function listModelProviders(){try{return await puter.ai.listModelProviders();}catch(e){console.warn("PuterAI.listModelProviders",e);return [];}}
  async function resolveModel(preferred){
    const models=await listModels();
    if(!Array.isArray(models)||!models.length)return preferred;
    const ids=models.map(m=>(m&&(m.id||m.name))||String(m));
    if(ids.includes(preferred))return preferred;
    const base=String(preferred).split("-")[0];
    return ids.find(id=>String(id).includes(base))||preferred;
  }
  function extractJSON(text){
    if(!text)return null;
    const t=String(text).replace(/\\`\\`\\`json|\\`\\`\\`/g,"").trim();
    try{return JSON.parse(t);}catch(_){}
    const m=t.match(/\\{[\\s\\S]*\\}/);
    if(!m)return null;
    try{return JSON.parse(m[0]);}catch(_){return null;}
  }
  function guard(obj){
    if(!obj||typeof obj!=="object")return null;
    const out={
      layer:obj.layer||"?",
      agrees:!!obj.agrees,
      confidence:typeof obj.confidence==="number"?Math.max(0,Math.min(1,obj.confidence)):0.5,
      concerns:Array.isArray(obj.concerns)?obj.concerns.slice(0,10).map(String):[],
      verdict_recommendation:VERDICTS.includes(String(obj.verdict_recommendation||"").toUpperCase())?String(obj.verdict_recommendation).toUpperCase():null,
      notes:String(obj.notes||"").slice(0,600)
    };
    FORBIDDEN.forEach(k=>{if(k in out)delete out[k];});
    return out;
  }
  const SYS="You are a market-data VALIDATION layer inside an options terminal. Only verify, cross-check and flag deterministic engine output. NEVER invent a strike, entry, stop-loss or target. Confidence is not a win rate. Return ONE JSON object: {layer, agrees, confidence, concerns[], flagged_strikes[], verdict_recommendation (CALL BUY, PUT BUY, WAIT, NO QUALIFYING TRADE, or null), notes}.";
  async function chatLayer(layer,digest){
    const model=await resolveModel(layer.env);
    const prompt=SYS+"\nLayer role: "+layer.role+"\nEngine output:\n"+JSON.stringify(digest);
    const opts={model,temperature:0.1,max_tokens:900};
    if(layer.web)opts.tools=[{type:"web_search"}];
    let resp;
    try{resp=await puter.ai.chat(prompt,opts);}catch(e){return{layer:layer.id,model,error:String(e)};}
    const text=typeof resp==="string"?resp:(resp&&resp.message&&resp.message.content)||(resp&&resp.text)||JSON.stringify(resp);
    const parsed=guard(extractJSON(text))||{layer:layer.id,agrees:false,concerns:["unparsed output"],model};
    parsed.model=model;
    return parsed;
  }
  async function runSixLayers(digest){
    if(!available())return LAYERS.map(l=>({layer:l.id,model:l.env,agrees:false,concerns:["Puter.js unavailable"]}));
    return Promise.all(LAYERS.map(l=>chatLayer(l,digest)));
  }
  return{available,listModels,listModelProviders,resolveModel,runSixLayers,LAYERS,guard};
})();