import{S as i}from"./index-fhkBm_-l.js";import"./helperFunctions-B2ihBp_A.js";import"./hdrFilteringFunctions-B99jTRbK.js";import"./pbrBRDFFunctions-68rA4HJQ.js";import"./index-EvByIPOY.js";import"./vendor-vue-Bt897R15.js";import"./vendor-primevue-CIbVuvmJ.js";const r="hdrIrradianceFilteringPixelShader",e=`#include<helperFunctions>
#include<importanceSampling>
#include<pbrBRDFFunctions>
#include<hdrFilteringFunctions>
uniform samplerCube inputTexture;
#ifdef IBL_CDF_FILTERING
uniform sampler2D icdfTexture;
#endif
uniform vec2 vFilteringInfo;uniform float hdrScale;varying vec3 direction;void main() {vec3 color=irradiance(inputTexture,direction,vFilteringInfo,0.0,vec3(1.0),direction
#ifdef IBL_CDF_FILTERING
,icdfTexture
#endif
);gl_FragColor=vec4(color*hdrScale,1.0);}`;i.ShadersStore[r]||(i.ShadersStore[r]=e);const m={name:r,shader:e};export{m as hdrIrradianceFilteringPixelShader};
