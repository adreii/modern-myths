# Town plan: one believable town for every episode

Every set from `locations.md` becomes a real building in one connected town, so any episode can cut from the square to the school to someone's kitchen and it all feels like the same place. Interiors are real rooms inside the buildings. Each building's street-side wall is a **cutaway wall**: it's there for exterior shots and hidden by the shot script for interior shots. That's how sitcom sets and dollhouse cameras work.

## Map (top view, north is up)

The square is **enclosed on all four sides** by buildings that face onto it, with a narrow street running round it like a market square.

```
        x: -140    -100   -73       -45            0            45      73      100      145
z -81            [Bakery][House1][House2][House3][House4][BakerHouse]              north side (built)
z -57   ══════════╬═══════ Bakery Road ═══════════════════════════════╬═══════════
z -36             ║  [APARTMENT ]  ┌──────── Town Square ────────┐  [SNEAKERS ]  ║  [          ]
z -18             ║  [ BLOCK    ]  │                              │  [CAFE     ]  ║  [  ARENA / ]
z   0             ║  [ 3 floors ]  │   fountain, benches, trees   │  [CORNER   ]  ║  [COMMUNITY ]
z  18             ║  [LIBRARY   ]  │                              │  [RESTAUR. ]  ║  [  HALL    ]
z  36             ║  [          ]  └──────────────────────────────┘  [LAUNDRY  ]  ║
z  54   ══════════╬═══════ Square Road South ═════════════════════════╬═══════════
z  73             ║        [TOY SHOP] [ TOWN HALL + clock tower ] [MUSIC SHOP]  ║
z 100   ══════════╬═══════ School Road ═══════════════════════════════╬═══════════
z 125     [ PARK      ]      [ SCHOOLYARD + basketball court ]   [HERO'S HOUSE][garage]
z 155     [ playground]      [ SCHOOL: classrooms, hallway,  ]   [  garden          ]
z 170     [ pond, bench]     [ cafeteria, hall with stage    ]
```

A ring street runs round the square on the west, east and south sides (Bakery Road is the north side). Avenues (║) at x = −100 and x = +100 join Bakery Road, Square Road South and School Road.

## Buildings and what's inside

| Building | Where | Interiors | Episodes |
|---|---|---|---|
| Bakery street: Bakery, 4 houses, Baker's house | North (built) | Baker's house gets her bedroom inside (replaces the separate set at x = 150) | 01 |
| Town square | Centre (built) | — | 01, 02, 06 |
| **School** (2 storeys) + yard and court | South, across School Road | Hallway with lockers, classroom, cafeteria, hall with a stage | 02, 03, 06, 07, 08 |
| **Hero's house** (2 storeys) + garage + garden | South-east | Kitchen and living room downstairs, bedroom upstairs (the room kit moves in here), garage | 01, 02, 03, 05, 06, 07, 08 |
| **Market Street shops** | East side of the square, facing it | Sneaker shop, café, corner shop, restaurant pickup counter, laundromat | 02, 04, 06, 08 |
| **Apartment block** (3 storeys) + **library** | West side of the square, facing it | Lobby, stairwell, hallway with numbered doors | 04, 06 |
| **Town Hall** with clock tower, toy shop, music shop | South side of the square, facing it | Town Hall's main room doubles as an event hall or awards stage | 07, plus landmarks for every wide shot |
| **Arena / community hall** | Far east | Wrestling ring with stands (stage version for events) | 05, 07 |
| **Park** + playground | South-west | Bench, paths, trees | 03 |

## Build phases
1. **Streets and shells:** School Road, both avenues, sidewalks, street lamps, a bigger ground, and every building's exterior with doors and windows. After this the town reads as a town from any angle.
2. **Interiors, most-used first:** Hero's house (moves the room kit in), the school, the shops, the Baker's bedroom.
3. **Dressing:** signs, parked cars, bins, fences, crowd spots, the CC0 props from Kenney/Quaternius.

Everything stays a rebuildable script (`roblox/Build/BuildTown*.luau`) with camera markers per location, the same way as EP01. EP01's shots keep working: the square and bakery street don't move. They just gain real buildings in the background.

## After the town: revamping EP01's camera
Once the town stands, EP01 gets a full camera pass using the episode skill's cinematography guide:
- a contrast/affinity map across the five beats
- a power flip in angles and shot sizes at the turn
- the doorstep echo kept, plus a "Why" note per shot
- shots that now use the richer background: shops behind the square, the school in the crane-up, the Baker's real bedroom
