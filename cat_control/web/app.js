import * as THREE from './vendor/three.module.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

const canvas = document.getElementById('room');
const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:false, powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.06;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x081522);
scene.fog = new THREE.Fog(0x0d1b2a, 20, 58);
const camera = new THREE.PerspectiveCamera(48, 1, .1, 90);

function standard(color, roughness=.76, metalness=.02) {
  return new THREE.MeshStandardMaterial({color, roughness, metalness});
}
const materials = {
  grass:standard(0x2e504b,.96), grassLight:standard(0x3f6657,.96), path:standard(0x746962,.93),
  stone:standard(0x55646a,.9), stoneLight:standard(0x8b9895,.9), wood:standard(0x654335,.86),
  woodDark:standard(0x302621,.9), leaf:standard(0x183b34,.91), leafLight:standard(0x2c5b48,.91),
  fur:standard(0xb65d36,.88), furLight:standard(0xe3a05b,.88), furDark:standard(0x713522,.9),
  cream:standard(0xf0d6ab,.93), white:standard(0xf4f2e8,.82), ink:standard(0x18231f,.74),
  pink:standard(0xd88382,.8), collar:standard(0x3e7e83,.46,.12), gold:standard(0xd7ab51,.34,.38),
  blue:standard(0x4f8fa1,.38,.06), red:standard(0xb7564e,.72), fabric:standard(0x354d61,.98),
  crate:standard(0x866044,.88), crateDark:standard(0x4e392d,.92), trash:standard(0x64706c,.96),
  lamp:standard(0x29231d,.52,.3), lampGlow:new THREE.MeshBasicMaterial({color:0xffc978}),
};
const waterMaterial = new THREE.MeshPhysicalMaterial({color:0x70c4d8, roughness:.12, metalness:0, transmission:.18, transparent:true, opacity:.82});
const glassMaterial = new THREE.MeshPhysicalMaterial({color:0xd8f1ed, roughness:.08, transmission:.55, transparent:true, opacity:.5});

function mesh(geometry, material, position=[0,0,0], rotation=[0,0,0], parent=scene) {
  const object = new THREE.Mesh(geometry, material);
  object.position.set(...position); object.rotation.set(...rotation);
  object.castShadow = true; object.receiveShadow = true; parent.add(object); return object;
}
function part(parent, geometry, material, position, name='') {
  const object = mesh(geometry, material, position, [0,0,0], parent); object.name=name; return object;
}
function capsule(radius, length, material, position, parent) {
  return part(parent, new THREE.CapsuleGeometry(radius,length,5,12), material, position);
}

const interactables = {};
const platforms = [];
function buildWorld() {
  mesh(new THREE.PlaneGeometry(38,34), materials.grass, [0,-.03,0], [-Math.PI/2,0,0]);
  // Stone route gives the scene direction without reducing the usable area.
  for (let i=0;i<18;i++) {
    const angle=i*.33, radius=2.7+i*.48;
    const stone=mesh(new THREE.CylinderGeometry(.62+.08*(i%3),.7,.10,12), i%2?materials.path:materials.stoneLight,
      [Math.sin(angle)*radius,.03,Math.cos(angle)*radius],[0,angle*.8,0]);
    stone.scale.z=.68;
  }
  buildFence();
  buildTree(-11,-8,1.0); buildTree(11,-8,.92); buildTree(-12,8,.86); buildTree(12,7,1.06);
  buildShrub(-8,10,.9); buildShrub(8,10,1.1); buildShrub(-9,-1,.78); buildShrub(10,1,.84);
  buildWaterStation(7,-6);
  buildRestDeck(-7,-6);
  buildTrainingArch(0,-12.6);
  buildTunnel(8,7);
  buildStreetLamp(-6,-2); buildStreetLamp(5,4); buildStreetLamp(-2,10); buildStreetLamp(12,-9);
  buildCrate(2,-4,0.95); buildCrate(4,-4.5,0.72); buildCrate(-3,5,.85);
  buildLitterPile(-10,3); buildLitterPile(11,3.5); buildLitterPile(-5,-10);
  mesh(new THREE.CircleGeometry(2.2,48), new THREE.MeshBasicMaterial({color:0x6c8b69,transparent:true,opacity:.25,depthWrite:false}), [0,.01,4.4],[-Math.PI/2,0,0]);
}
function buildStreetLamp(x,z) {
  const root=new THREE.Group(); root.position.set(x,0,z); scene.add(root);
  mesh(new THREE.CylinderGeometry(.09,.13,3.2,10),materials.lamp,[0,1.6,0],[0,0,0],root);
  mesh(new THREE.CylinderGeometry(.28,.34,.09,16),materials.lamp,[0,3.17,0],[0,0,0],root);
  const glow=mesh(new THREE.SphereGeometry(.18,18,12),materials.lampGlow,[0,3.04,0],[0,0,0],root);
  const light=new THREE.PointLight(0xffbf72,3.6,8,2); light.position.set(x,2.95,z); light.castShadow=true; light.shadow.mapSize.set(256,256); scene.add(light);
  glow.material=glow.material.clone(); glow.material.color.set(0xffd58a);
}
function buildCrate(x,z,scale=1) {
  const root=new THREE.Group(); root.position.set(x,.38*scale,z); root.scale.setScalar(scale); scene.add(root);
  mesh(new THREE.BoxGeometry(1.15,.76,1.05),materials.crate,[0,0,0],[0,.12,0],root);
  for (const y of [-.26,.26]) mesh(new THREE.BoxGeometry(1.22,.065,.06),materials.crateDark,[0,y,-.54],[0,.12,0],root);
  for (const sx of [-.47,.47]) mesh(new THREE.BoxGeometry(.06,.62,.06),materials.crateDark,[sx,0,-.55],[0,.12,0],root);
  mesh(new THREE.BoxGeometry(.06,.7,.06),materials.crateDark,[0,0,-.56],[0,.12,0],root);
  platforms.push({x,z,halfWidth:.575*scale,halfDepth:.525*scale,height:.76*scale,yaw:.12});
}
function buildLitterPile(x,z) {
  const root=new THREE.Group(); root.position.set(x,0,z); scene.add(root);
  for (const [px,py,pz,s,rot] of [[0,.18,0,.7,.1],[-.45,.13,.12,.52,-.3],[.45,.12,-.08,.6,.22]]) {
    const bag=part(root,new THREE.DodecahedronGeometry(.45,1),materials.trash,[px,py,pz]); bag.scale.set(s,.72*s,s*.8); bag.rotation.z=rot;
  }
  mesh(new THREE.BoxGeometry(.55,.05,.34),materials.path,[.05,.5,-.12],[.1,.2,.2],root);
}
function buildFence() {
  const xLimit=17.8,zLimit=15.8;
  for (let x=-17.5;x<=17.5;x+=2.5) {
    for (const z of [-zLimit,zLimit]) {
      mesh(new THREE.BoxGeometry(.16,1.35,.16),materials.woodDark,[x,.67,z]);
      mesh(new THREE.BoxGeometry(2.55,.13,.13),materials.wood,[x,.52,z]);
      mesh(new THREE.BoxGeometry(2.55,.13,.13),materials.wood,[x,1.04,z]);
    }
  }
  for (let z=-15;z<=15;z+=2.5) {
    for (const x of [-xLimit,xLimit]) {
      mesh(new THREE.BoxGeometry(.16,1.35,.16),materials.woodDark,[x,.67,z]);
      mesh(new THREE.BoxGeometry(.13,.13,2.55),materials.wood,[x,.52,z]);
      mesh(new THREE.BoxGeometry(.13,.13,2.55),materials.wood,[x,1.04,z]);
    }
  }
}
function buildTree(x,z,scale=1) {
  const root=new THREE.Group(); root.position.set(x,0,z); root.scale.setScalar(scale); scene.add(root);
  mesh(new THREE.CylinderGeometry(.38,.55,3.4,10),materials.wood,[0,1.7,0],[0,.1,0],root);
  for (const [px,py,pz,s] of [[0,3.7,0,1.3],[-.8,3.4,.15,.9],[.75,3.5,.25,.92],[.15,4.25,-.25,.85]]) {
    const crown=part(root,new THREE.IcosahedronGeometry(1.15,2),py>4?materials.leafLight:materials.leaf,[px,py,pz]); crown.scale.set(s,s*.82,s);
  }
  for (let i=0;i<4;i++) mesh(new THREE.SphereGeometry(.08,10,8),materials.red,[(i-1.5)*.42,3.7+(i%2)*.55,.8-(i%3)*.22],[0,0,0],root);
}
function buildShrub(x,z,scale=1) {
  const root=new THREE.Group(); root.position.set(x,0,z); root.scale.setScalar(scale); scene.add(root);
  for (const [px,py,pz,s] of [[0,.48,0,.72],[-.5,.38,.1,.55],[.48,.39,-.05,.58],[.05,.35,.48,.52]]) {
    const leaf=part(root,new THREE.IcosahedronGeometry(1,1),materials.leafLight,[px,py,pz]); leaf.scale.set(s,s*.72,s);
  }
}
function buildWaterStation(x,z) {
  const station=new THREE.Group(); station.position.set(x,0,z); scene.add(station);
  mesh(new THREE.CylinderGeometry(1.45,1.58,.24,40),materials.stone,[0,.12,0],[0,0,0],station);
  mesh(new THREE.CylinderGeometry(1.17,1.32,.32,40),materials.white,[0,.32,0],[0,0,0],station);
  const water=mesh(new THREE.CylinderGeometry(1.0,1.0,.06,48),waterMaterial,[0,.51,0],[0,0,0],station);
  const fountain=mesh(new THREE.CylinderGeometry(.17,.25,1.25,18),materials.stone,[0,1.0,0],[0,0,0],station);
  mesh(new THREE.SphereGeometry(.32,18,12),materials.stoneLight,[0,1.67,0],[0,0,0],station);
  const stream=mesh(new THREE.CylinderGeometry(.045,.045,.88,12),glassMaterial,[0,1.06,0],[0,0,0],station);
  const ripples=[];
  for (const radius of [.42,.72,.94]) {
    const ring=mesh(new THREE.TorusGeometry(radius,.018,8,48),materials.white,[0,.56,0],[Math.PI/2,0,0],station);
    ring.material=ring.material.clone(); ring.material.transparent=true; ring.material.opacity=.48; ripples.push(ring);
  }
  interactables.water={position:new THREE.Vector3(x,0,z),root:station,water,fountain,stream,ripples};
}
function buildRestDeck(x,z) {
  const deck=new THREE.Group(); deck.position.set(x,0,z); scene.add(deck);
  mesh(new THREE.BoxGeometry(5,.28,4),materials.wood,[0,.14,0],[0,0,0],deck);
  for (let i=-2;i<=2;i++) mesh(new THREE.BoxGeometry(.045,.02,3.7),materials.woodDark,[i*.9,.3,0],[0,0,0],deck);
  const bed=mesh(new THREE.CylinderGeometry(1.2,1.35,.34,32),materials.fabric,[0,.52,0],[0,0,0],deck);
  mesh(new THREE.CylinderGeometry(.85,1.0,.16,32),materials.cream,[0,.76,0],[0,0,0],deck);
  for (const xLeg of [-2.05,2.05]) for (const zLeg of [-1.55,1.55]) mesh(new THREE.CylinderGeometry(.07,.08,.8,10),materials.woodDark,[xLeg,.66,zLeg],[0,0,0],deck);
  interactables.rest={position:new THREE.Vector3(x,0,z),root:deck,bed};
}
function buildTrainingArch(x,z) {
  const arch=new THREE.Group(); arch.position.set(x,0,z); scene.add(arch);
  mesh(new THREE.BoxGeometry(.38,3.2,.38),materials.wood,[-2.0,1.6,0],[0,0,0],arch);
  mesh(new THREE.BoxGeometry(.38,3.2,.38),materials.wood,[2.0,1.6,0],[0,0,0],arch);
  mesh(new THREE.BoxGeometry(4.4,.38,.5),materials.woodDark,[0,3.12,0],[0,0,0],arch);
  for (let i=-3;i<=3;i++) mesh(new THREE.SphereGeometry(.10,10,8),i%2?materials.gold:materials.red,[i*.48,2.73,.28],[0,0,0],arch);
  interactables.arch={position:new THREE.Vector3(x,0,z)};
}
function buildTunnel(x,z) {
  const root=new THREE.Group(); root.position.set(x,0,z); root.rotation.y=-.45; scene.add(root);
  for (let i=0;i<18;i++) {
    const a=Math.PI*i/17;
    mesh(new THREE.BoxGeometry(.16,.16,3.2),materials.fabric,[Math.cos(a)*1.35,Math.sin(a)*1.35,0],[0,0,a+Math.PI/2],root);
  }
  interactables.tunnel={position:new THREE.Vector3(x,0,z)};
}

function makeWhisker(parent, side, y, tilt) {
  const points=[new THREE.Vector3(side*.25,y,-.76),new THREE.Vector3(side*.68,y+tilt,-.93),new THREE.Vector3(side*1.03,y+tilt*1.4,-1.02)];
  const curve=new THREE.CatmullRomCurve3(points);
  return part(parent,new THREE.TubeGeometry(curve,10,.012,5,false),materials.cream,[0,0,0]);
}
function buildLeg(parent,x,z,index) {
  const hip=new THREE.Group(); hip.position.set(x,.9,z); parent.add(hip);
  const upper=capsule(.19,.48,materials.fur,[0,-.31,0],hip);
  const ankle=new THREE.Group(); ankle.position.set(0,-.64,0); hip.add(ankle);
  const lower=capsule(.17,.28,materials.furLight,[0,-.18,-.02],ankle);
  const paw=part(ankle,new THREE.SphereGeometry(.26,18,12),materials.cream,[0,-.43,-.13]); paw.scale.set(1.1,.62,1.3);
  for (const toeX of [-.1,0,.1]) { const toe=part(ankle,new THREE.SphereGeometry(.035,8,6),materials.pink,[toeX,-.48,-.37]); toe.scale.y=.55; }
  return {hip,ankle,upper,lower,paw,index};
}
function buildTail(parent) {
  const base=new THREE.Group(); base.position.set(.62,1.24,.78); base.rotation.x=-.5; base.rotation.y=-.18; parent.add(base);
  const joints=[]; let cursor=base;
  for (let i=0;i<7;i++) {
    const joint=new THREE.Group(); joint.position.set(0,0,i?.36:0); cursor.add(joint);
    const segment=capsule(i>4?.10:.13,.23,i>4?materials.furDark:materials.furLight,[0,0,.19],joint); segment.rotation.x=Math.PI/2;
    joints.push(joint); cursor=joint;
  }
  return {base,joints};
}
function buildCat() {
  const root=new THREE.Group(); root.name='Mikan'; scene.add(root);
  const rig=new THREE.Group(); root.add(rig);
  const body=part(rig,new THREE.SphereGeometry(1,36,24),materials.fur,[0,1.18,.16]); body.scale.set(.78,.82,1.28);
  const rump=part(rig,new THREE.SphereGeometry(.72,32,22),materials.furLight,[0,1.15,.78]); rump.scale.set(1.04,.94,1.18);
  const chest=part(rig,new THREE.SphereGeometry(.55,24,18),materials.cream,[0,1.12,-.86]); chest.scale.set(.82,1.05,.35);
  const headPivot=new THREE.Group(); headPivot.position.set(0,1.72,-1.12); headPivot.scale.set(.80,.86,.88); rig.add(headPivot);
  const head=part(headPivot,new THREE.SphereGeometry(.82,32,22),materials.furLight,[0,0,0]); head.scale.set(1.03,1.0,.94);
  const cheekL=part(headPivot,new THREE.SphereGeometry(.36,22,16),materials.cream,[-.28,-.19,-.7]); cheekL.scale.set(1,.72,.48);
  const cheekR=part(headPivot,new THREE.SphereGeometry(.36,22,16),materials.cream,[.28,-.19,-.7]); cheekR.scale.set(1,.72,.48);
  const nose=part(headPivot,new THREE.SphereGeometry(.095,14,10),materials.pink,[0,-.13,-.94]); nose.scale.set(1.1,.72,.65);
  const mouth=part(headPivot,new THREE.TorusGeometry(.11,.018,6,16,Math.PI),materials.furDark,[0,-.28,-.91]); mouth.rotation.z=Math.PI;
  const earShape=new THREE.Shape(); earShape.moveTo(-.28,0); earShape.lineTo(0,.65); earShape.lineTo(.28,0); earShape.closePath();
  const earGeometry=new THREE.ExtrudeGeometry(earShape,{depth:.16,bevelEnabled:true,bevelSegments:3,steps:1,bevelSize:.045,bevelThickness:.045});
  const earL=part(headPivot,earGeometry,materials.furLight,[-.45,.5,-.10]); earL.rotation.z=-.09;
  const earR=part(headPivot,earGeometry,materials.furLight,[.45,.5,-.10]); earR.rotation.z=.09;
  const innerGeometry=new THREE.ShapeGeometry(earShape);
  const innerL=part(headPivot,innerGeometry,materials.pink,[-.45,.55,-.15]); innerL.scale.set(.66,.66,1); innerL.rotation.y=Math.PI; innerL.rotation.z=-.09;
  const innerR=part(headPivot,innerGeometry,materials.pink,[.45,.55,-.15]); innerR.scale.set(.66,.66,1); innerR.rotation.y=Math.PI; innerR.rotation.z=.09;
  const eyes=[],pupils=[],lids=[];
  for (const x of [-.29,.29]) {
    const eye=part(headPivot,new THREE.SphereGeometry(.115,20,14),materials.white,[x,.08,-.825]); eye.scale.set(1,.95,.30); eyes.push(eye);
    const iris=part(headPivot,new THREE.SphereGeometry(.068,22,16),materials.gold,[x,.08,-.875]); iris.scale.set(1,1,.25);
    const pupil=part(headPivot,new THREE.SphereGeometry(.033,14,10),materials.ink,[x,.08,-.904]); pupil.scale.set(.72,1.32,.22); pupils.push(pupil);
    const glint=part(headPivot,new THREE.SphereGeometry(.014,10,8),materials.white,[x-.018,.105,-.922]); glint.scale.set(1,1,.25);
    const lid=part(headPivot,new THREE.SphereGeometry(.12,20,10),materials.furLight,[x,.15,-.872]); lid.scale.set(1,.1,.31); lids.push(lid);
  }
  for (const side of [-1,1]) for (const [y,tilt] of [[-.18,.03],[-.28,-.01],[-.37,-.05]]) makeWhisker(headPivot,side,y,tilt);
  // Fur markings, collar and bell add definition at normal gameplay distance.
  for (const [x,y,z,rz] of [[0,.55,-.69,0],[-.22,.52,-.67,-.25],[.22,.52,-.67,.25]]) {
    const stripe=part(headPivot,new THREE.CapsuleGeometry(.035,.25,3,8),materials.furDark,[x,y,z]); stripe.rotation.z=rz;
  }
  for (const [z,length] of [[-.08,.36],[.28,.43],[.62,.35]]) {
    const stripe=part(rig,new THREE.CapsuleGeometry(.035,length,3,8),materials.furDark,[0,1.91,z]); stripe.rotation.z=Math.PI/2;
  }
  const collar=part(rig,new THREE.TorusGeometry(.52,.075,12,36),materials.collar,[0,1.58,-.78]); collar.rotation.x=Math.PI/2;
  const bell=part(rig,new THREE.SphereGeometry(.13,16,12),materials.gold,[0,1.43,-1.27]);
  const legs=[buildLeg(rig,-.43,-.56,0),buildLeg(rig,.43,-.56,1),buildLeg(rig,-.46,.72,2),buildLeg(rig,.46,.72,3)];
  const tail=buildTail(rig);
  root.userData={rig,body,rump,chest,headPivot,head,ears:[earL,earR],eyes,pupils,lids,legs,tail,collar,bell};
  return root;
}

buildWorld();
const cat=buildCat();
scene.add(new THREE.HemisphereLight(0x7699c1,0x172332,1.55));
const sun=new THREE.DirectionalLight(0xa8c4eb,2.35); sun.position.set(-8,14,9); sun.castShadow=true; sun.shadow.mapSize.set(2048,2048);
sun.shadow.camera.left=-22; sun.shadow.camera.right=22; sun.shadow.camera.top=22; sun.shadow.camera.bottom=-22; sun.shadow.bias=-.00025; scene.add(sun);
const fill=new THREE.DirectionalLight(0x83abc8,.72); fill.position.set(10,7,-8); scene.add(fill);

const classes=['back','else','five','forward','left','one','right','skip','stop','three','two'];
const labels={back:'Backward',else:'Idle',five:'Raise Paw',forward:'Forward',left:'Turn Left',one:'Slow Walk',right:'Turn Right',skip:'Jump',stop:'Stop',three:'Sprint',two:'Trot'};
const spawn=new THREE.Vector3(0,0,4.4);
cat.position.copy(spawn);
let cameraOrbit=2.55;
camera.position.copy(spawn).add(new THREE.Vector3(0,3.9,8.4).applyAxisAngle(new THREE.Vector3(0,1,0),cameraOrbit));
camera.lookAt(spawn.clone().add(new THREE.Vector3(0,1.25,0)));
let elapsedTime=0,lastFrameTime=performance.now();
let targetYaw=0,currentSpeed=0,targetSpeed=0,currentTurn=0,targetTurn=0;
let lastUpdate=0,lastGesture='else',gesture='else',waveStarted=-10;
let verticalSpeed=0,grounded=true,jumpRequested=false,jumpTravelSpeed=0,lastStateReceived=performance.now();
let gaitPhase=0,gaitBlend=0,trotBlend=0,airPoseBlend=0,landingCompression=0,waveBlend=0,drinkBlend=0;
let actualSpeed=0,actualTurn=0;
const gravity=11.4;
let catMixer=null;
const catLoader=new GLTFLoader();
const catAssetUrl=new URL('./assets/bicolor_cat.glb',import.meta.url);
catLoader.load(catAssetUrl.href, (gltf)=>{
  const visual=gltf.scene;
  visual.name='BicolorCatVisual';
  const bounds=new THREE.Box3().setFromObject(visual);
  const size=bounds.getSize(new THREE.Vector3());
  const scale=2.45/Math.max(size.y,1e-3);
  visual.scale.setScalar(scale);
  const scaledBounds=new THREE.Box3().setFromObject(visual);
  visual.position.y=-scaledBounds.min.y+.02;
  visual.rotation.y=Math.PI;
  visual.traverse((node)=>{
    if(node.isMesh){ node.castShadow=true; node.receiveShadow=true; }
  });
  const findBone=(fragment)=>{
    let match=null;
    visual.traverse((node)=>{ if(!match&&node.isBone&&node.name.includes(fragment)) match=node; });
    return match;
  };
  cat.userData.modelBones={
    leftFrontHip:findBone('Wolf_l_FrontLeg_Hip'),
    leftFrontKnee:findBone('Wolf_l_FrontLeg_Knee'),
    leftFrontAnkle:findBone('Wolf_l_FrontLeg_Ankle'),
    leftFrontBall:findBone('Wolf_l_FrontLeg_Ball'),
    rightFrontHip:findBone('Wolf_r_FrontLeg_Hip'),
    rightFrontKnee:findBone('Wolf_r_FrontLeg_Knee'),
    rightFrontAnkle:findBone('Wolf_r_FrontLeg_Ankle'),
    rightFrontBall:findBone('Wolf_r_FrontLeg_Ball'),
    leftHindHip:findBone('Wolf_l_HindLeg_Hip'),
    leftHindKnee:findBone('Wolf_l_HindLeg_Knee1'),
    leftHindHock:findBone('Wolf_l_HindLeg_Knee2'),
    leftHindAnkle:findBone('Wolf_l_HindLeg_Ankle'),
    leftHindBall:findBone('Wolf_l_HindLeg_Ball'),
    rightHindHip:findBone('Wolf_r_HindLeg_Hip'),
    rightHindKnee:findBone('Wolf_r_HindLeg_Knee1'),
    rightHindHock:findBone('Wolf_r_HindLeg_Knee2'),
    rightHindAnkle:findBone('Wolf_r_HindLeg_Ankle'),
    rightHindBall:findBone('Wolf_r_HindLeg_Ball'),
    spine:findBone('Wolf_Spine_01'),
    spineMid:findBone('Wolf_Spine_03'),
    spineTop:findBone('Wolf_Spine_Top'),
    neck:findBone('Wolf_Neck_01'),
    neckMid:findBone('Wolf_Neck_02'),
    neckTop:findBone('Wolf_Neck_Top'),
    head:findBone('Wolf_Head_Jaw'),
    tail:findBone('Wolf_Tail_01_02'),
    tailMid:findBone('Wolf_Tail_01_03'),
    tailTip:findBone('Wolf_Tail_01_04'),
    tailEnd:findBone('Wolf_Tail_01_05'),
  };
  cat.userData.modelRest={};
  for(const [key,bone] of Object.entries(cat.userData.modelBones)) if(bone) cat.userData.modelRest[key]=bone.quaternion.clone();
  cat.userData.modelVisual=visual;
  cat.userData.modelBaseY=visual.position.y;
  cat.userData.modelFeet=['Wolf_l_FrontLeg_Toe','Wolf_r_FrontLeg_Toe','Wolf_l_HindLeg_Toe','Wolf_r_HindLeg_Toe','Wolf_l_FrontLeg_Ball','Wolf_r_FrontLeg_Ball','Wolf_l_HindLeg_Ball','Wolf_r_HindLeg_Ball'].map(findBone).filter(Boolean);
  cat.userData.rig.visible=false;
  cat.userData.modelLoaded=true;
  cat.add(visual);
  if(gltf.animations.length){
    // The asset only supplies an idle clip. Keep its facial expressions;
    // locomotion below owns all articulated bones and never adds Euler deltas.
    const expressionTracks=gltf.animations[0].tracks.filter(track=>track.name.includes('morphTargetInfluences'));
    if(expressionTracks.length){
      catMixer=new THREE.AnimationMixer(visual);
      cat.userData.modelAction=catMixer.clipAction(new THREE.AnimationClip('Expressions',gltf.animations[0].duration,expressionTracks));
      cat.userData.modelAction.play();
    }
  }
}, undefined, (error)=>console.warn('Bicolor Cat asset unavailable; using procedural fallback.',error));

function resetCat() {
  cat.position.copy(spawn); cat.rotation.set(0,0,0); targetYaw=0; currentSpeed=0; targetSpeed=0; currentTurn=0; targetTurn=0; cameraOrbit=2.55; gesture='else';
  verticalSpeed=0; grounded=true; jumpRequested=false; jumpTravelSpeed=0; lastGesture='else';
  gaitPhase=0; gaitBlend=0; trotBlend=0; airPoseBlend=0; landingCompression=0; waveBlend=0; drinkBlend=0; actualSpeed=0; actualTurn=0;
}
function applyState(state) {
  if (state.updated===lastUpdate) return;
  lastUpdate=state.updated;
  const safeGesture=classes.includes(state.gesture)?state.gesture:'else';
  const changed=safeGesture!==lastGesture;
  lastGesture=safeGesture; gesture=safeGesture;
  targetSpeed=({forward:1.35,back:-.9,one:.52,two:1.75,three:3.05}[gesture]||0);
  targetTurn=gesture==='left'?1.55:gesture==='right'?-1.55:0;
  if (gesture==='skip'&&changed&&grounded) jumpRequested=true;
  if (gesture==='five'&&changed) waveStarted=elapsedTime;
}
function nearestZone() {
  const zones=[['Water Station',interactables.water.position,2.4],['Crate Yard',interactables.rest.position,3.2],['Lamp Arch',interactables.arch.position,3.3],['Old Pipe',interactables.tunnel.position,3.0]];
  for (const zone of zones) if (cat.position.distanceTo(zone[1])<zone[2]) return zone;
  return ['Central Alley',new THREE.Vector3(),0];
}
function animateWorld(t) {
  const water=interactables.water;
  water.water.position.y=.51+Math.sin(t*1.7)*.012;
  water.stream.scale.y=.84+Math.sin(t*3.2)*.08;
  water.ripples.forEach((ring,index)=>{ const cycle=(t*.28+index*.31)%1; ring.scale.setScalar(.75+cycle*.42); ring.material.opacity=(1-cycle)*.42; });
}
function platformCoordinates(platform,x,z) {
  const dx=x-platform.x,dz=z-platform.z,c=Math.cos(platform.yaw),s=Math.sin(platform.yaw);
  return {x:c*dx-s*dz,z:s*dx+c*dz};
}
function insidePlatform(platform,x,z,margin=0) {
  const local=platformCoordinates(platform,x,z);
  return Math.abs(local.x)<=platform.halfWidth+margin&&Math.abs(local.z)<=platform.halfDepth+margin;
}
function moveCharacter(dt,forward) {
  if (jumpRequested&&grounded) {
    verticalSpeed=5.75; grounded=false; jumpRequested=false;
    jumpTravelSpeed=Math.max(1.55,currentSpeed);
  }
  const travelSpeed=!grounded&&gesture==='skip'?jumpTravelSpeed:currentSpeed;
  const previousY=cat.position.y;
  const next=cat.position.clone().addScaledVector(forward,travelSpeed*dt);
  // Resolve box sides in local coordinates; raised feet clear the obstacle.
  for (const platform of platforms) {
    if (previousY>=platform.height-.035||!insidePlatform(platform,next.x,next.z,.26)) continue;
    const local=platformCoordinates(platform,next.x,next.z);
    const px=platform.halfWidth+.26-Math.abs(local.x),pz=platform.halfDepth+.26-Math.abs(local.z);
    if (px<pz) local.x=Math.sign(local.x||1)*(platform.halfWidth+.26);
    else local.z=Math.sign(local.z||1)*(platform.halfDepth+.26);
    const c=Math.cos(platform.yaw),s=Math.sin(platform.yaw);
    next.x=platform.x+c*local.x+s*local.z;
    next.z=platform.z-s*local.x+c*local.z;
  }
  cat.position.x=THREE.MathUtils.clamp(next.x,-16.4,16.4);
  cat.position.z=THREE.MathUtils.clamp(next.z,-14.4,14.4);
  const supports=platforms.filter(platform=>insidePlatform(platform,cat.position.x,cat.position.z,.06)&&previousY>=platform.height-.04);
  const floor=supports.reduce((height,platform)=>Math.max(height,platform.height),0);
  if (grounded&&previousY>floor+.04) grounded=false;
  if (!grounded) {
    verticalSpeed-=gravity*dt;
    cat.position.y+=verticalSpeed*dt;
    if (verticalSpeed<=0&&cat.position.y<=floor) {cat.position.y=floor;verticalSpeed=0;grounded=true;}
  } else cat.position.y=floor;
}
const poseEuler=new THREE.Euler(),poseDelta=new THREE.Quaternion(),poseTarget=new THREE.Quaternion(),footPosition=new THREE.Vector3();
function stepSample(cycle,duty) {
  cycle=((cycle%1)+1)%1;
  if(cycle<duty) return {sweep:Math.cos(Math.PI*cycle/duty),lift:0};
  const swing=(cycle-duty)/(1-duty);
  return {sweep:-Math.cos(Math.PI*swing),lift:Math.pow(Math.sin(Math.PI*swing),1.4)};
}
function animateModel(t,dt,motionSpeed,waving,drinking) {
  const bones=cat.userData.modelBones,rest=cat.userData.modelRest,visual=cat.userData.modelVisual;
  if(!bones||!visual) return;
  const angles=Object.fromEntries(Object.keys(bones).map(key=>[key,[0,0,0]]));
  const legs=[['leftFront',0,0,1,false],['rightFront',.5,.5,-1,false],['leftHind',.75,.5,1,true],['rightHind',.25,0,-1,true]];
  for(const [prefix,walkOffset,trotOffset,side,hind] of legs){
    const walk=stepSample(gaitPhase/(Math.PI*2)+walkOffset,.64);
    const trot=stepSample(gaitPhase/(Math.PI*2)+trotOffset,.52);
    // Opposite signed travel on the two sides makes pivot turns step in place.
    const legSpeed=actualSpeed-side*actualTurn*.52;
    const direction=Math.tanh(legSpeed/.2);
    const amplitude=Math.min(.48,.2+Math.abs(legSpeed)*.095)*gaitBlend;
    const sweep=THREE.MathUtils.lerp(walk.sweep,trot.sweep,trotBlend)*amplitude*direction;
    const lift=THREE.MathUtils.lerp(walk.lift,trot.lift,trotBlend)*gaitBlend;
    let hip,knee,hock=0,ankle;
    if(hind){
      hip=sweep*.84-lift*.10;
      knee=-sweep*.22-lift*.24;
      hock=sweep*.12+lift*.64;
      ankle=-(hip+knee+hock)+lift*.16;
    }else{
      hip=sweep+lift*.08;
      knee=-sweep*.42+lift*.48;
      ankle=-(hip+knee)+lift*.12;
    }
    hip=THREE.MathUtils.lerp(hip,hind?.25:.5,airPoseBlend);
    knee=THREE.MathUtils.lerp(knee,hind?-.55:.48,airPoseBlend);
    hock=THREE.MathUtils.lerp(hock,.82,airPoseBlend);
    ankle=THREE.MathUtils.lerp(ankle,hind?-.52:-.62,airPoseBlend);
    hip+=landingCompression*(hind?.15:-.12);
    knee+=landingCompression*(hind?-.28:.3);
    hock+=landingCompression*.28;
    ankle-=landingCompression*.18;
    angles[`${prefix}Hip`][0]=hip;
    angles[`${prefix}Knee`][0]=knee;
    angles[`${prefix}Ankle`][0]=ankle;
    angles[`${prefix}Ball`][0]=-lift*.14*(1-airPoseBlend);
    if(hind) angles[`${prefix}Hock`][0]=hock;
  }
  waveBlend=THREE.MathUtils.damp(waveBlend,waving&&grounded?1:0,8,dt);
  drinkBlend=THREE.MathUtils.damp(drinkBlend,drinking&&grounded?1:0,5,dt);
  angles.leftFrontHip[0]=THREE.MathUtils.lerp(angles.leftFrontHip[0],.85+Math.sin(t*8)*.07,waveBlend);
  angles.leftFrontKnee[0]=THREE.MathUtils.lerp(angles.leftFrontKnee[0],.5,waveBlend);
  angles.leftFrontAnkle[0]=THREE.MathUtils.lerp(angles.leftFrontAnkle[0],-.55+Math.sin(t*8)*.12,waveBlend);
  const sway=Math.sin(gaitPhase)*gaitBlend*(1-airPoseBlend);
  angles.spine[2]=sway*.013;
  angles.spineMid[0]=Math.sin(gaitPhase*2)*gaitBlend*.02+Math.sin(t*2.2)*.008;
  angles.spineTop[0]=drinkBlend*.08;
  angles.spineTop[2]=-actualTurn*.025;
  angles.neck[0]=drinkBlend*.26-airPoseBlend*.1;
  angles.neckMid[0]=drinkBlend*.18;
  angles.neckTop[0]=drinkBlend*(.24+Math.sin(t*7)*.018)+Math.sin(t*.8)*.015*(1-drinkBlend);
  angles.neckTop[1]=Math.sin(t*.45)*.045*(1-gaitBlend)*(1-drinkBlend)-actualTurn*.035;
  angles.head[0]=drinkBlend*Math.max(0,Math.sin(t*7))*.035;
  ['tail','tailMid','tailTip','tailEnd'].forEach((key,index)=>{
    angles[key][0]=Math.sin(t*1.45-index*.42)*(.035+index*.012)+sway*.018;
    angles[key][2]=Math.sin(t*1.1-index*.35)*.025+actualTurn*.025-airPoseBlend*.07;
  });
  const blend=1-Math.exp(-dt*14);
  for(const [key,bone] of Object.entries(bones)){
    if(!bone||!rest[key]) continue;
    const [x,y,z]=angles[key];
    poseDelta.setFromEuler(poseEuler.set(x,y,z));
    poseTarget.copy(rest[key]).multiply(poseDelta);
    bone.quaternion.slerp(poseTarget,blend).normalize();
  }
  visual.position.y=cat.userData.modelBaseY;
  if(grounded){
    // A shared height correction prevents toe penetration on the current
    // support plane. This is not per-foot locking or inverse kinematics.
    visual.updateWorldMatrix(true,true);
    let lowest=Infinity;
    for(const foot of cat.userData.modelFeet) lowest=Math.min(lowest,foot.getWorldPosition(footPosition).y);
    if(Number.isFinite(lowest)) visual.position.y+=cat.position.y+.02-lowest;
  }
  cat.userData.motion={phase:gaitPhase,weight:gaitBlend,speed:actualSpeed,turn:actualTurn,trot:trotBlend,air:airPoseBlend,landing:landingCompression};
}
function animateCat(t,dt) {
  const before=cat.position.clone(),previousYaw=cat.rotation.y,wasGrounded=grounded,impactSpeed=Math.max(0,-verticalSpeed);
  currentSpeed=THREE.MathUtils.damp(currentSpeed,targetSpeed,5.5,dt);
  currentTurn=THREE.MathUtils.damp(currentTurn,targetTurn,7.5,dt);
  targetYaw+=currentTurn*dt;
  const yawDelta=Math.atan2(Math.sin(targetYaw-cat.rotation.y),Math.cos(targetYaw-cat.rotation.y));
  cat.rotation.y+=yawDelta*Math.min(1,dt*9);
  const forward=new THREE.Vector3(0,0,-1).applyAxisAngle(new THREE.Vector3(0,1,0),cat.rotation.y);
  moveCharacter(dt,forward);
  actualSpeed=THREE.MathUtils.damp(actualSpeed,cat.position.clone().sub(before).dot(forward)/Math.max(dt,.001),10,dt);
  actualTurn=THREE.MathUtils.damp(actualTurn,(cat.rotation.y-previousYaw)/Math.max(dt,.001),10,dt);
  const speed=Math.abs(actualSpeed),motionSpeed=Math.hypot(actualSpeed,actualTurn*.52),moving=motionSpeed>.035;
  gaitBlend=THREE.MathUtils.damp(gaitBlend,grounded?THREE.MathUtils.smoothstep(motionSpeed,.025,.3):0,9,dt);
  trotBlend=THREE.MathUtils.damp(trotBlend,THREE.MathUtils.smoothstep(speed,.8,2.5),5,dt);
  gaitPhase=(gaitPhase+dt*Math.PI*2*(.58+motionSpeed*.50)*gaitBlend)%(Math.PI*2);
  airPoseBlend=THREE.MathUtils.damp(airPoseBlend,grounded?0:1,grounded?11:7,dt);
  if(!wasGrounded&&grounded) landingCompression=Math.min(1,Math.max(.25,impactSpeed/6));
  else landingCompression=THREE.MathUtils.damp(landingCompression,0,8,dt);
  const phase=gaitPhase;
  if(catMixer) catMixer.update(dt);
  const zone=nearestZone(),atWater=zone[0]==='Water Station';
  // stop and else share the same neutral locomotion state.  Stop retains
  // the contextual drinking interaction when the cat is at the water zone.
  const drinking=gesture==='stop'&&atWater;
  const sitting=false;
  const breathing=Math.sin(t*2.2)*.018;
  cat.userData.rig.position.y=.30+breathing+(moving?Math.abs(Math.sin(phase))*.055:0);
  cat.userData.rig.rotation.z=moving?Math.sin(phase*.5)*.025:THREE.MathUtils.damp(cat.userData.rig.rotation.z,0,7,dt);
  cat.userData.body.scale.y=THREE.MathUtils.damp(cat.userData.body.scale.y,sitting?.68:.82,8,dt);
  cat.userData.rump.position.y=THREE.MathUtils.damp(cat.userData.rump.position.y,sitting?.88:1.15,8,dt);
  cat.userData.legs.forEach((leg,index)=>{
    const gait=Math.sin(phase+(index%2?Math.PI:0))*(moving?.48:0);
    leg.hip.rotation.x=THREE.MathUtils.damp(leg.hip.rotation.x,gait,13,dt);
    leg.ankle.rotation.x=THREE.MathUtils.damp(leg.ankle.rotation.x,moving?-.18-Math.max(0,gait)*.3:0,12,dt);
  });
  const waveAge=t-waveStarted,waving=waveAge>=0&&waveAge<1.65;
  animateModel(t,dt,motionSpeed,waving,drinking);
  const leftFront=cat.userData.legs[0];
  leftFront.hip.rotation.z=THREE.MathUtils.damp(leftFront.hip.rotation.z,waving?-.95+Math.sin(t*11)*.18:0,11,dt);
  leftFront.hip.rotation.x=THREE.MathUtils.damp(leftFront.hip.rotation.x,waving?-.45:leftFront.hip.rotation.x,11,dt);
  cat.userData.headPivot.position.y=THREE.MathUtils.damp(cat.userData.headPivot.position.y,drinking?1.25:(sitting?1.55:1.72),8,dt);
  cat.userData.headPivot.rotation.x=THREE.MathUtils.damp(cat.userData.headPivot.rotation.x,drinking?-.42:(moving?.04:Math.sin(t*.8)*.025),8,dt);
  cat.userData.headPivot.rotation.y=THREE.MathUtils.damp(cat.userData.headPivot.rotation.y,moving?Math.sin(t*.9)*.05:Math.sin(t*.42)*.12,5,dt);
  const blink=(t%4.8)>4.58;
  cat.userData.lids.forEach(lid=>lid.scale.y=THREE.MathUtils.damp(lid.scale.y,blink?1.0:.1,22,dt));
  cat.userData.ears[0].rotation.z=-.09+Math.sin(t*.8)*.025;
  cat.userData.ears[1].rotation.z=.09-Math.sin(t*.72)*.022;
  cat.userData.tail.joints.forEach((joint,index)=>{ joint.rotation.y=Math.sin(t*2.0-index*.42)*(.16+index*.018); joint.rotation.x=-.045+Math.sin(t*1.35+index*.3)*.035; });
  cat.userData.bell.rotation.z=Math.sin(phase)*Math.min(.18,speed*.08);
  document.getElementById('location').textContent=zone[0];
  document.getElementById('interaction').textContent=!grounded?'Airborne':cat.position.y>.1?'On Crate':drinking?'Drinking':atWater?'Water Station Ready':zone[0]==='Crate Yard'?'Crate Zone':zone[0]==='Old Pipe'?'Pipe Challenge':'Free Roam';
}
function followCamera(dt) {
  const moving=Math.abs(currentSpeed)>.08||Math.abs(currentTurn)>.08;
  cameraOrbit=THREE.MathUtils.damp(cameraOrbit,moving?.68:2.55,2.2,dt);
  const offset=new THREE.Vector3(0,3.9,8.4).applyAxisAngle(new THREE.Vector3(0,1,0),cat.rotation.y+cameraOrbit);
  const desired=cat.position.clone().add(offset);
  camera.position.lerp(desired,1-Math.exp(-dt*3.4));
  camera.lookAt(cat.position.clone().add(new THREE.Vector3(0,1.25,0)));
}
function resize() {
  const width=Math.max(1,canvas.clientWidth),height=Math.max(1,canvas.clientHeight),ratio=renderer.getPixelRatio();
  if (canvas.width!==Math.floor(width*ratio)||canvas.height!==Math.floor(height*ratio)) {
    renderer.setSize(width,height,false); camera.aspect=width/height; camera.updateProjectionMatrix();
  }
}
function renderState(state) {
  const safeGesture=classes.includes(state.gesture)?state.gesture:'else';
  applyState({...state,gesture:safeGesture});
  const cameraMode=state.mode==='camera';
  const previewCard=document.getElementById('preview-card');
  const preview=document.getElementById('processed-preview');
  previewCard.hidden=!cameraMode;
  if (cameraMode&&!preview.getAttribute('src')) preview.setAttribute('src',preview.dataset.src);
  if (!cameraMode&&preview.getAttribute('src')) preview.removeAttribute('src');
  const cameraError=/unavailable|failed|error/i.test(state.message||'');
  const gateState=state.motion_gate_active?'GATE STOP':state.motion_gate_armed?'GATE ARMED':state.motion_gate_enabled?(state.motion_ready?'GATE PASS':'GATE WARMUP'):'GATE OFF';
  const saved=Number.isFinite(state.classifier_skip_rate)?`${(state.classifier_skip_rate*100).toFixed(0)}% KMD SKIPPED`:'0% KMD SKIPPED';
  document.getElementById('preview-state').textContent=cameraError?'CAMERA ERROR':`${gateState} · ${saved}`;
  document.getElementById('mode').textContent=state.mode==='camera'?'CAMERA':'DEMO';
  document.getElementById('gesture').textContent=labels[safeGesture];
  document.getElementById('gesture-code').textContent=safeGesture;
  document.getElementById('confidence').textContent=state.motion_gate_active
    ? `Frame-Diff Gate · Motion ${((state.motion_average||0)*100).toFixed(3)}%`
    : `Confidence ${state.confidence?(state.confidence*100).toFixed(1)+'%':'--'}`;
  document.getElementById('action').textContent=safeGesture==='else'?'Idle':(state.action_label||labels[safeGesture]);
  document.getElementById('score').textContent=state.score;
  document.getElementById('energy').style.width=`${state.energy}%`;
  document.getElementById('energy-text').textContent=`${state.energy}%`;
  document.getElementById('toast').textContent=state.message;
  document.getElementById('fps').textContent=state.mode==='camera'?`KMD · ${state.fps||'--'} FPS · ${state.device||'CPU'}`:'INTERACTIVE DEMO';
  document.querySelectorAll('.gesture-grid button').forEach(button=>button.classList.toggle('active',button.dataset.gesture===safeGesture));
}
async function poll() {
  try {
    const response=await fetch('/api/state',{cache:'no-store',signal:AbortSignal.timeout(800)});
    if (!response.ok) throw new Error('State unavailable');
    const state=await response.json();
    lastStateReceived=performance.now(); renderState(state);
  } catch (_) {}
  setTimeout(poll,120);
}
function makeButtons() {
  const grid=document.getElementById('gesture-grid');
  classes.forEach(value=>{ const button=document.createElement('button'); button.textContent=labels[value]; button.dataset.gesture=value; button.title=value; button.onclick=()=>fetch('/api/demo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({gesture:value})}); grid.appendChild(button); });
}
document.getElementById('reset').addEventListener('click',resetCat);
renderer.setAnimationLoop((now)=>{
  resize();
  const dt=Math.min(Math.max((now-lastFrameTime)/1000,0),.05);
  lastFrameTime=now; elapsedTime+=dt;
  if (now-lastStateReceived>1000) {
    targetSpeed=0; currentSpeed=0; targetTurn=0; currentTurn=0; gesture='else'; lastGesture='else'; jumpRequested=false;
    document.getElementById('toast').textContent='Connection lost. Character stopped.';
    document.getElementById('gesture').textContent='Idle'; document.getElementById('gesture-code').textContent='else';
    document.getElementById('action').textContent='Idle';
  }
  animateWorld(elapsedTime); animateCat(elapsedTime,dt); followCamera(dt); renderer.render(scene,camera);
});
makeButtons(); poll();
