import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {Workbook, SpreadsheetFile} from 'file:///C:/Users/qiwen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root='C:/Users/qiwen/Desktop/new_exp/qwen25_05b';
const out='C:/Users/qiwen/Desktop/study/mbti/outputs/qwen25_05b_20261026';
const metrics=['mae','rmse','mape','mask_mae','mask_rmse','mask_mape'];
const records=[];
for(const ent of (await fs.readdir(root,{withFileTypes:true})).filter(x=>x.isDirectory()&&x.name!=='launches').sort((a,b)=>a.name.localeCompare(b.name))){
 const source=path.join(root,ent.name,'experiments.log');
 const lines=(await fs.readFile(source,'utf8')).split(/\r?\n/);
 const conf={};
 for(const m of lines[0].matchAll(/(\w+)=('(?:[^']*)'|\[[^\]]*\]|[^,)]*)/g)){
  let v=m[2]; conf[m[1]]=v.startsWith("'")?v.slice(1,-1):v==='True'?true:v==='False'?false:v==='None'?null:Number.isFinite(Number(v))?Number(v):v;
 }
 const tests=lines.map((line,i)=>({line,n:i+1})).filter(x=>x.line.includes('[Test][prediction] best model'));
 assert.equal(tests.length,1,ent.name);
 const test=tests[0], vectors={}, overall={};
 for(const k of metrics){
  vectors[k]=JSON.parse(test.line.match(new RegExp('(?:^| )'+k+':(\\[[^\\]]*\\])'))[1]);
  overall[k]=Number(test.line.match(new RegExp('overall_'+k+':([\\d.eE+-]+)'))[1]);
  assert.equal(vectors[k].length,conf.output_dim);
  assert.ok(Math.abs(vectors[k].reduce((a,b)=>a+b,0)/vectors[k].length-overall[k])<0.000002);
 }
 const epochs=lines.flatMap(x=>{const m=x.match(/INFO - epoch (\d+) train_loss:/);return m?[Number(m[1])]:[];});
 const par=lines.find(x=>x.includes('total_params:')).match(/total_params:(\d+)\s+total_trainable_params:(\d+)/);
 records.push({name:ent.name.replace(/^.*?\d{2}_\d{2}_\d{2}_/,'').replace(/_DGT_.*$/,''),conf,vectors,overall,source,line:test.n,epochs:epochs.length,lastEpoch:Math.max(...epochs),total:Number(par[1]),trainable:Number(par[2]),start:lines[0].slice(0,19),end:test.line.slice(0,19),stop:lines.some(x=>x.endsWith('early stop'))?'早停':'达到配置轮数'});
}
assert.equal(records.length,11);
const wb=Workbook.create();
function makeSheet(name,title,notes,headers,rows,widths){
 const sh=wb.worksheets.add(name);sh.showGridLines=false;
 const end=headers.length,n=rows.length+5;
 sh.getRangeByIndexes(0,0,n,end).format.font={name:'Arial',size:10,color:'#243247'};
 sh.getRange('A2').values=[[title]];sh.getRange('A2').format.font={size:15,bold:true,color:'#203D62'};
 notes.forEach((note,i)=>{sh.getRangeByIndexes(2+i,0,1,1).values=[[note]];});
 sh.getRangeByIndexes(4,0,1,end).values=[headers];
 sh.getRangeByIndexes(5,0,rows.length,end).values=rows;
 const head=sh.getRangeByIndexes(4,0,1,end);head.format={fill:'#203D62',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',rowHeight:30};
 sh.getRangeByIndexes(5,0,rows.length,end).format.rowHeight=26;
 sh.getRangeByIndexes(5,0,rows.length,end).format.verticalAlignment='center';
 widths.forEach((w,i)=>sh.getRangeByIndexes(4,i,rows.length+1,1).format.columnWidth=w);
 for(let r=0;r<rows.length;r++)if(r%2===1)sh.getRangeByIndexes(r+5,0,1,end).format.fill='#F1F5FA';
 sh.freezePanes.freezeRows(5);sh.freezePanes.freezeColumns(1);
 sh.tables.add(sh.getRangeByIndexes(4,0,rows.length+1,end),true,'Table'+wb.worksheets.items.length);
 return sh;
}
const sum=makeSheet('测试结果','Qwen2.5-0.5B 实验测试结果',[
 '11 个数据集；每个数据集 1 次实验，seed=42；取日志中最终 best model 测试结果。',
 'MAPE 按百分比显示；普通与 mask 指标分别保留。各数据集量纲不同，不做跨数据集平均或排名。'
],['数据集','MAE','RMSE','MAPE','mask MAE','mask RMSE','mask MAPE','输入步数','预测步数','输出通道数','训练轮数','停止方式'],records.map(r=>[r.name,...metrics.map(k=>r.overall[k]),r.conf.sample_len,r.conf.predict_len,r.conf.output_dim,r.epochs,r.stop]),[16,13,13,13,13,14,15,12,12,14,12,18]);
sum.getRange('B6:G16').setNumberFormat('0.000000');sum.getRange('D6:D16').setNumberFormat('0.00%');sum.getRange('G6:G16').setNumberFormat('0.00%');
sum.getRange('A19').values=[['口径说明']];sum.getRange('A19').format.font={bold:true};
sum.getRange('A20').values=[['overall 数值直接保留日志精度（6 位小数）；逐通道原始精度见“通道明细”。']];
sum.getRange('A21').values=[['METR_LA、PEMS_BAY 的普通 MAE/RMSE 与 mask MAE/RMSE 不同，请按所需评测口径选用。']];
sum.getRange('A22').values=[['双通道含义和 mask 定义未在本目录说明；不推断其业务含义。未提供逐预测步指标。']];
sum.getRange('A23').values=[['训练轮数为日志中 train_loss 记录数（epoch 从 0 开始）；这些结果不包含多随机种子的均值与标准差。']];
const channels=records.flatMap(r=>r.vectors.mae.map((_,i)=>[r.name,i+1,...metrics.map(k=>r.vectors[k][i]),`${r.source}:${r.line}`]));
const ch=makeSheet('通道明细','逐输出通道测试结果',['通道编号按最终测试日志中的数组顺序，从 1 开始。','MAE / RMSE 保留原始数值；MAPE 单元格保存原始小数比例，显示为百分比。'],['数据集','输出通道','MAE','RMSE','MAPE','mask MAE','mask RMSE','mask MAPE','来源日志与行号'],channels,[16,12,15,15,14,15,15,15,100]);
ch.getRangeByIndexes(5,2,channels.length,6).setNumberFormat('0.000000');
ch.getRangeByIndexes(5,4,channels.length,1).setNumberFormat('0.00%');ch.getRangeByIndexes(5,7,channels.length,1).setNumberFormat('0.00%');
const configHeaders=['数据集','实际 dataset 参数','数据文件（原运行环境）','邻接文件（原运行环境）','训练比例','验证比例','测试比例（推算）','输入步数','预测步数','输入维数','输出维数','模型','预训练模型','seed','batch size','学习率','LLM 学习率倍率','dropout','weight decay','LLM 层数','LoRA rank','训练损失','模型选择指标','总参数量','可训练参数量','开始时间（日志）','测试时间（日志）','来源日志','最终测试行号'];
const configRows=records.map(r=>{const c=r.conf;return[r.name,c.dataset,c.data_path,c.adj_filename,c.train_ratio,c.val_ratio,null,c.sample_len,c.predict_len,c.input_dim,c.output_dim,c.model,c.qwen_model_path,c.seed,c.batch_size,c.learning_rate,c.llm_lr_scale,c.dropout,c.weight_decay,c.llm_layers,c.compact_lora_rank,c.training_loss,c.selection_metric,r.total,r.trainable,r.start,r.end,r.source,r.line];});
const ds=makeSheet('数据集与配置','数据集对应关系与实验配置',['数据集标识、文件路径和参数均来自各实验日志首行 Namespace；来源日志列可用于追溯。','当前目录仅有日志、loss.png 和启动配置，无原始 .npz / .csv 数据；原运行环境路径不代表本机文件存在。'],configHeaders,configRows,[16,23,75,75,12,12,20,12,12,12,12,18,65,10,13,13,21,13,17,13,13,25,19,16,18,24,24,105,17]);
for(let i=0;i<records.length;i++)ds.getRange(`G${i+6}`).formulas=[[`=1-E${i+6}-F${i+6}`]];
ds.getRange('E6:G16').setNumberFormat('0.0%');ds.getRange('P6:P16').setNumberFormat('0.0000');ds.getRange('R6:R16').setNumberFormat('0.00');ds.getRange('S6:S16').setNumberFormat('0.00000');ds.getRange('X6:Y16').setNumberFormat('#,##0');
ds.getRange('A19').values=[['PEMS03 / PEMS04 / PEMS07 / PEMS08 的实际参数分别为 PEMS03FLOW / PEMS04FLOW / PEMS07FLOW / PEMS08FLOW。']];
ds.getRange('A20').values=[['测试比例按 1−训练比例−验证比例推算，实际样本数量与划分边界未在日志中提供。']];
sum.getRange('A24').values=[['LLM 层数：HZMETRO 为 12，BJMETRO 为 2，其余为 1；详细配置见数据集与配置。']];
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'测试结果!A5:L16',include:'values,formulas',tableMaxRows:12,tableMaxCols:12,maxChars:6000})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:30},summary:'公式错误检查'})).ndjson);
for(const [sheetName,range,file] of [['测试结果','A1:L24','summary'],['通道明细','A1:H21','channels'],['数据集与配置','A1:D16','datasets'],['数据集与配置','L5:U16','model_config']]){
 const p=await wb.render({sheetName,range,scale:1.5,format:'png'});await fs.writeFile(`${out}/${file}.png`,new Uint8Array(await p.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(`${out}/QWEN25_05B_实验结果汇总.xlsx`);
await fs.writeFile(`${out}/extracted.json`,JSON.stringify(records,null,2));
console.log(JSON.stringify({experiments:records.length,channels:channels.length,output:`${out}/QWEN25_05B_实验结果汇总.xlsx`}));
