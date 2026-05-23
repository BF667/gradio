import{S as i}from"./index-DcmFC6R-.js";import"./bakedVertexAnimation-BI_POxc5.js";import"./instancesDeclaration-BzrJzQkO.js";import"./morphTargetsVertex-CTl4oYUW.js";import"./index-ZCI6Jh3f.js";import"./vendor-vue-Bt897R15.js";import"./vendor-primevue-CIbVuvmJ.js";const e="iblVoxelGridVertexShader",o=`attribute vec3 position;varying vec3 vNormalizedPosition;
#include<bonesDeclaration>
#include<bakedVertexAnimationDeclaration>
#include<instancesDeclaration>
#include<morphTargetsVertexGlobalDeclaration>
#include<morphTargetsVertexDeclaration>[0..maxSimultaneousMorphTargets]
uniform mat4 invWorldScale;uniform mat4 viewMatrix;void main(void) {vec3 positionUpdated=position;
#include<morphTargetsVertexGlobal>
#include<morphTargetsVertex>[0..maxSimultaneousMorphTargets]
#include<instancesVertex>
#include<bonesVertex>
#include<bakedVertexAnimation>
vec4 worldPos=finalWorld*vec4(positionUpdated,1.0);gl_Position=viewMatrix*invWorldScale*worldPos;vNormalizedPosition.xyz=gl_Position.xyz*0.5+0.5;
#ifdef IS_NDC_HALF_ZRANGE
gl_Position.z=gl_Position.z*0.5+0.5;
#endif
}`;i.ShadersStore[e]||(i.ShadersStore[e]=o);const c={name:e,shader:o};export{c as iblVoxelGridVertexShader};
