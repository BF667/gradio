import{S as o}from"./index-CyPKAAxX.js";import"./index-O4LwJxin.js";import"./vendor-vue-Bt897R15.js";import"./vendor-primevue-CIbVuvmJ.js";const r="oitFinalSimpleBlendPixelShader",t=`var uFrontColor: texture_2d<f32>;@fragment
fn main(input: FragmentInputs)->FragmentOutputs {var fragCoord: vec2i=vec2i(fragmentInputs.position.xy);var frontColor: vec4f=textureLoad(uFrontColor,fragCoord,0);fragmentOutputs.color=frontColor;}
`;o.ShadersStoreWGSL[r]||(o.ShadersStoreWGSL[r]=t);const m={name:r,shader:t};export{m as oitFinalSimpleBlendPixelShaderWGSL};
