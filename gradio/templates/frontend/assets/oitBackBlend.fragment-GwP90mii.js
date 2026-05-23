import{S as r}from"./index-DcmFC6R-.js";import"./index-ZCI6Jh3f.js";import"./vendor-vue-Bt897R15.js";import"./vendor-primevue-CIbVuvmJ.js";const t="oitBackBlendPixelShader",e=`var uBackColor: texture_2d<f32>;@fragment
fn main(input: FragmentInputs)->FragmentOutputs {fragmentOutputs.color=textureLoad(uBackColor,vec2i(fragmentInputs.position.xy),0);if (fragmentOutputs.color.a==0.0) {discard;}}
`;r.ShadersStoreWGSL[t]||(r.ShadersStoreWGSL[t]=e);const s={name:t,shader:e};export{s as oitBackBlendPixelShaderWGSL};
