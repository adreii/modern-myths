# Locations: every planned episode, and the sets to build

Episodes 2–8 only have a premise in the corpus tracker. The one-line stories below are **proposals**, written to the episode skill's rules: kids 8–13, an absurd rule stated with a straight face, no copyable stunts. They exist to work out where each episode happens. When an episode is properly written with the episode skill, its places may shift a little; update this file then.

## Episodes → places

| Ep | Absurd premise (proposed for 02–08) | Places | Key props |
|---|---|---|---|
| 01 Everyone Has a Number 🔢 | *Built.* Everyone's number floats over their head; the baker with 9 quietly feeds the street | Town square, bakery street, baker's bedroom | Numbers, bread, basket, bag |
| 02 The Sneakers 👟 | At my school, sneakers talk, but all they ever say is their price. The quietest pair belongs to the kid who actually helps people | Kid's bedroom, sneaker shop, school hallway, schoolyard | Talking shoes (speech bubbles), shoe boxes, display wall, lockers |
| 03 The 5AM Routine ⏰ | Kids get a "busy streak" counter; I never stop doing things, until I slowly turn into a grey statue. Grandma's nap brings the colour back | Kid's bedroom (dawn and night), kitchen, classroom, park bench | Streak counter, alarm clocks (too many), homework pile, blanket |
| 04 The Delivery Guy 📦 | In our building, delivery people are literally see-through. I learn one courier's name and he slowly becomes visible | Apartment hallway and front door, building exterior at night (rain), restaurant pickup counter | Delivery bag, scooter, rain, delivery-app screen |
| 05 The Wrestling Match 🤼 | The crowd boos the masked villain every week; backstage the "villain" is the one sharing his sandwich with the "hero" | Wrestling arena (ring, stands, spotlights), backstage corridor, living room with TV | Ring and ropes, masks, belt, TV, sandwich |
| 06 The Gotcha Video 📱 | A classmate trips in the cafeteria; a kid's video of it follows her everywhere as a giant screen over her head. Then we see the rest of her day | School cafeteria, hallway, her bedroom, kid's bedroom (scrolling) | Phones, giant floating video screen, lunch trays |
| 07 The Self-Made Man 🏆 | I win the science fair "all by myself", and the trophy gets heavier for every helper I leave out of my speech | School hall stage, kitchen table, classroom, garage workshop | Trophy, podium, volcano project, tools |
| 08 Whiter Than White 🧼 | In my house everything is "whiter than white" and glows like an advert; at school at night, the janitor nobody notices is the one making things shine | Kitchen (advert-bright), school at night, laundromat | Glowing surfaces, spray bottles, mop cart, washing machines |

## Sets to build, by how many episodes reuse them

| # | Set | Episodes | Covers | Build |
|---|---|---|---|---|
| 1 | **Town exterior** | 01, 02, 04, 08 | Square, street, house fronts, sidewalk, night and rain versions | **Done** (BuildEP01Map). Add: a row of shopfronts, an apartment block, street lamps, rain |
| 2 | **Home room kit** | 01, 02, 03, 04, 05, 06, 07, 08 | Bedroom, kitchen, living room; one open-front room builder plus furniture presets per room type | Script one modular room (walls, window, door, ceiling), then furniture sets |
| 3 | **School kit** | 02, 03, 06, 07, 08 | Hallway with lockers, classroom, cafeteria, hall with a stage, schoolyard | Corridor module + rooms from the room kit; the hall stage doubles for the science fair |
| 4 | **Phone / screen overlay** (a UI, not a place) | 01, 02, 03, 04, 06 | Feeds, counters, streaks, delivery app, viral video, giant floating screen | One ScreenGui/BillboardGui template with swappable content (built on NumberBillboard) |
| 5 | **Shop kit** | 02, 04, 08 | Sneaker shop, restaurant counter, laundromat | One shop shell + counter, shelves, display wall, sign swaps |
| 6 | **Arena** | 05 | Ring, crowd stands, spotlights, backstage corridor | Stands and lights reuse the crowd rigs; the corridor reuses the school corridor module |
| 7 | **Apartment block** | 04 | Lobby, stairwell, hallway with numbered doors | Corridor module + door numbers |
| 8 | **Garage workshop** | 07 | Workbench, tools, half-built project | Room kit + props |

**Suggested build order:**
1. Home room kit (needed in every episode).
2. School kit (five episodes).
3. Phone/screen overlay.

Those three plus the existing town cover nearly all of EP02, EP03, EP06 and EP08. Shop kit, arena and apartment block come when their episodes are next.

**How we'd construct them:** the same way as EP01. A build script per set, so every set is rebuildable, all laid out side by side in one "Backlot" area with camera markers. Simple shapes are scripted in Roblox parts to keep the blocky look. Detailed props (food, furniture, tools, appliances) can come from free CC0 kits, imported once into a shared prop library; see the sources below.

## Free asset sources (CC0)
Licences checked at the source on 2026-10-26. No ready-made CC0 *places* exist; the closest things are modular kits we assemble ourselves.

| Source | Licence | Best for | Use in which set |
|---|---|---|---|
| **Kenney**: kenney.nl/assets | CC0, commercial OK, credit optional (don't use the Kenney logo) | Chunky low-poly, closest to the Roblox look: City Kit (Suburban, Roads), Food Kit (200 items), nature, vehicles | Town additions, shopfronts, food props (bread, lunch trays, sandwiches) |
| **Quaternius**: quaternius.com | CC0, commercial OK, credit optional | Ultimate House Interior, Furniture packs, Ultimate Food / Junk Food, cars and public transport, Modular Streets, Downtown City MegaKit | Home room kit furniture, school and shop props, scooter/cars |
| **ambientCG**: ambientcg.com | CC0, credit optional | Materials and textures (wood floor, tiles, lockers' metal, carpet) | As MaterialVariants on our scripted parts. Use the **GL** normal maps, 1024 px or less |
| **Poly Haven**: polyhaven.com | CC0 | Skies (HDRIs) and textures. Its models are too realistic for this look | Skies, a few textures |
| Poly Pizza / OpenGameArt | **Mixed** licences, set per asset | Gap-fillers only | Only after confirming CC0 on the asset's own page; CC-BY needs a credit line |

**Avoid for monetized videos:** other creators' Toolbox / Creator Store models. Roblox only licenses them for use *on Roblox*; nothing grants off-platform use. Roblox's own Terms of Use couldn't be read automatically (the page blocked access), so read them yourself before monetizing (already on the to-do list).

**Getting them into Studio:**
- Import 3D takes **FBX, OBJ and glTF**, and can queue several files at once.
- A kit file with many objects comes in as one model of MeshParts.
- Each mesh can have at most **20,000 triangles**. Kenney and Quaternius pieces are far under that.
- Imported meshes upload to your account, and that upload may be checked by Roblox before others can see it. Plan for a delay the first time.

**Keep a record** (a simple sheet) for every pack: source URL, pack name and version, licence shown on the download date (screenshot it), author, date. Credit in the video description is optional for CC0 but good practice: *"Assets: Kenney (kenney.nl), Quaternius, ambientCG"*.
