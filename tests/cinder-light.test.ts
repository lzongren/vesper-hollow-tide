import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { Data3DTexture, PointLight } from "three";
import { Combat } from "../src/combat";
import { CinderFire, CinderLights } from "../src/cinder-fire";

test("shrine light sources follow all eight awakened vents from ignition to extinction", () => {
  const game = new Combat(2);
  game.boss.phase = 2;
  game.boss.attack = 2;
  game.emitAttack();
  const rig = new CinderLights();
  const lamps = rig.children as PointLight[];
  assert.equal(game.hazards.length, lamps.length);
  rig.update(game.hazards);
  assert.ok(lamps.every(light => light.intensity === 0));
  for (const h of game.hazards) h.age = h.delay + .35;
  rig.update(game.hazards);
  lamps.forEach((lamp, i) => {
    assert.equal(lamp.position.x, game.hazards[i].x);
    assert.equal(lamp.position.z, game.hazards[i].z);
    assert.ok(lamp.intensity > 30 && lamp.position.y > 1);
  });
  for (const h of game.hazards) h.age = h.life;
  rig.update(game.hazards);
  assert.ok(lamps.every(light => light.intensity === 0));
  rig.update([]);
  assert.equal(rig.children.length, 8);
});

test("both packed simulations rise through the volume and leave smoke above the source", () => {
  const data = gunzipSync(readFileSync(new URL("../public/textures/shrine-fire.rg8.gz",import.meta.url)));
  const [nx,ny,nz] = [40,52,40];
  assert.equal(data.length, nx*ny*nz*16*2*2);
  const centroids:number[] = [];
  for (let variant=0;variant<2;variant++) {
    for (const frame of [2,9,14]) {
      let mass=0, lift=0, smoke=0;
      for(let z=0;z<nz;z++) for(let y=0;y<ny;y++) for(let x=0;x<nx;x++) {
        const iy=y+Math.floor(frame/4)*ny, ix=x+(frame%4)*nx;
        const offset=2*((z+variant*nz)*16*nx*ny+iy*4*nx+ix);
        const hot=data[offset];
        mass+=hot;
        lift+=y*hot;
        if(y>ny*.35) smoke+=data[offset+1];
      }
      assert.ok(mass>0);
      if(frame===14)assert.ok(smoke>10000);
      centroids.push(lift/mass);
    }
  }
  assert.ok(centroids[1]>centroids[0]+4 && centroids[4]>centroids[3]+4);
  assert.notDeepEqual(centroids.slice(0,3),centroids.slice(3));
});

test("preheating draws only the stone and expiration hides the entire burst", () => {
  const fire=new CinderFire(3,{map:new Data3DTexture(),eddies:new Data3DTexture()});
  fire.burn(-1.35,.85);
  assert.equal(fire.visible,false);
  fire.burn(-.4,.85);
  assert.equal(fire.visible,true);
  assert.equal(fire.geometry.drawRange.count,6);
  fire.burn(0,.85);
  assert.equal(fire.geometry.drawRange.count,Infinity);
  fire.burn(.85,.85);
  assert.equal(fire.visible,false);
});

test("each vent produces its ignition cue once, where and when it becomes dangerous", () => {
  const game=new Combat(2);
  game.boss.phase=2;
  game.boss.attack=2;
  game.emitAttack();
  const vents=game.hazards.map(h=>({...h}));
  game.drainEvents();
  const heard:number[]=[];
  for(let i=0;i<305;i++){
    game.updateHazards(1/120);
    for(const e of game.drainEvents().filter(e=>e.kind==="ignition")){
      const h=vents.find(h=>h.id===e.value)!;
      const time=(i+1)/120;
      assert.ok(time>=h.delay-1e-8 && time<=h.delay+1/120+1e-8);
      assert.deepEqual([e.x,e.z],[h.x,h.z]);
      heard.push(h.id);
    }
  }
  assert.deepEqual(heard,vents.map(h=>h.id));
});
