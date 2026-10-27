class CaptureProcessor extends AudioWorkletProcessor {
  constructor(){super();this.block=new Float32Array(2048);this.offset=0;this.port.onmessage=e=>{if(e.data?.type==='flush'){if(this.offset){this.port.postMessage(this.block.slice(0,this.offset));this.block=new Float32Array(2048);this.offset=0;}this.port.postMessage({type:'flushed'});}};}
  process(inputs){const channel=inputs[0]?.[0];if(channel){for(let i=0;i<channel.length;i++){this.block[this.offset++]=channel[i];if(this.offset===this.block.length){this.port.postMessage(this.block);this.block=new Float32Array(2048);this.offset=0;}}}return true;}
}
registerProcessor('recorder-capture',CaptureProcessor);
