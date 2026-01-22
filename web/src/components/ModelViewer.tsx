import { useRef, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera } from '@react-three/drei'
import { Loader2, Box, AlertCircle, Layers } from 'lucide-react'
import * as THREE from 'three'
import { fetchModelMesh, ModelMesh } from '../api/client'

interface ModelViewerProps {
  modelId: number | null
  onBuildRequest?: () => void
}

function SurfaceMesh({ vertices, faces, color }: {
  vertices: number[][]
  faces: number[][]
  color: string
}) {
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()

    // Flatten vertices into a typed array
    const positions = new Float32Array(vertices.flat())
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    // Flatten faces into indices
    const indices = new Uint32Array(faces.flat())
    geo.setIndex(new THREE.BufferAttribute(indices, 1))

    // Compute normals for proper lighting
    geo.computeVertexNormals()

    return geo
  }, [vertices, faces])

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color={color}
        side={THREE.DoubleSide}
        flatShading
        roughness={0.7}
        metalness={0.1}
      />
    </mesh>
  )
}

function ModelScene({ meshData }: { meshData: ModelMesh }) {
  const groupRef = useRef<THREE.Group>(null)

  // Calculate center and scale for camera positioning
  const { center, scale } = useMemo(() => {
    const extent = meshData.extent
    const centerX = (extent.x_min + extent.x_max) / 2
    const centerY = (extent.y_min + extent.y_max) / 2
    const centerZ = (extent.z_min + extent.z_max) / 2

    const sizeX = extent.x_max - extent.x_min
    const sizeY = extent.y_max - extent.y_min
    const sizeZ = extent.z_max - extent.z_min
    const maxSize = Math.max(sizeX, sizeY, sizeZ)

    return {
      center: [centerX, centerY, centerZ] as [number, number, number],
      scale: maxSize,
    }
  }, [meshData.extent])

  // Camera distance based on model scale
  const cameraDistance = scale * 1.5

  return (
    <>
      <PerspectiveCamera
        makeDefault
        position={[center[0] + cameraDistance, center[1] + cameraDistance * 0.5, center[2] + cameraDistance]}
        fov={50}
      />
      <OrbitControls
        target={center}
        enableDamping
        dampingFactor={0.1}
        minDistance={scale * 0.5}
        maxDistance={scale * 5}
      />

      {/* Lighting */}
      <ambientLight intensity={0.5} />
      <directionalLight
        position={[center[0] + scale, center[1] + scale * 2, center[2] + scale]}
        intensity={1}
        castShadow
      />
      <directionalLight
        position={[center[0] - scale, center[1] + scale, center[2] - scale]}
        intensity={0.5}
      />

      {/* Model group */}
      <group ref={groupRef}>
        {meshData.surfaces.map((surface) => (
          <SurfaceMesh
            key={surface.surface_id}
            vertices={surface.vertices}
            faces={surface.faces}
            color={surface.color}
          />
        ))}
      </group>

      {/* Grid helper */}
      <gridHelper
        args={[scale * 2, 20, '#888888', '#444444']}
        position={[center[0], meshData.extent.z_min, center[2]]}
        rotation={[Math.PI / 2, 0, 0]}
      />
    </>
  )
}

function NoModelPlaceholder({ onBuildRequest }: { onBuildRequest?: () => void }) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50 text-gray-500">
      <Box className="w-12 h-12 mb-4 text-gray-300" />
      <p className="text-sm font-medium mb-2">No 3D Model</p>
      <p className="text-xs text-gray-400 mb-4 text-center px-4">
        Build a 3D model from valid DSL to see the visualization
      </p>
      {onBuildRequest && (
        <button
          onClick={onBuildRequest}
          className="px-4 py-2 text-sm bg-geo-600 text-white rounded-lg hover:bg-geo-700 transition-colors"
        >
          Build 3D Model
        </button>
      )}
    </div>
  )
}

function LoadingState() {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50">
      <Loader2 className="w-8 h-8 text-geo-500 animate-spin mb-4" />
      <p className="text-sm text-gray-500">Loading 3D model...</p>
    </div>
  )
}

function ErrorState({ error }: { error: Error }) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-red-50 text-red-600 p-4">
      <AlertCircle className="w-8 h-8 mb-4" />
      <p className="text-sm font-medium mb-2">Failed to load model</p>
      <p className="text-xs text-red-500 text-center">{error.message}</p>
    </div>
  )
}

function SurfaceLegend({ surfaces }: { surfaces: ModelMesh['surfaces'] }) {
  return (
    <div className="absolute bottom-2 left-2 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-2 max-w-[200px]">
      <div className="flex items-center gap-1 text-xs font-medium text-gray-700 mb-2">
        <Layers className="w-3 h-3" />
        <span>Surfaces</span>
      </div>
      <div className="space-y-1 max-h-32 overflow-y-auto">
        {surfaces.map((surface) => (
          <div key={surface.surface_id} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: surface.color }}
            />
            <span className="text-xs text-gray-600 truncate" title={surface.name}>
              {surface.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function ModelViewer({ modelId, onBuildRequest }: ModelViewerProps) {
  const { data: meshData, isLoading, error } = useQuery({
    queryKey: ['model-mesh', modelId],
    queryFn: () => fetchModelMesh(modelId!),
    enabled: modelId !== null,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  if (modelId === null) {
    return (
      <div className="relative h-full min-h-[300px] bg-gray-100 rounded-lg overflow-hidden">
        <NoModelPlaceholder onBuildRequest={onBuildRequest} />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="relative h-full min-h-[300px] bg-gray-100 rounded-lg overflow-hidden">
        <LoadingState />
      </div>
    )
  }

  if (error) {
    return (
      <div className="relative h-full min-h-[300px] bg-gray-100 rounded-lg overflow-hidden">
        <ErrorState error={error as Error} />
      </div>
    )
  }

  if (!meshData || meshData.surfaces.length === 0) {
    return (
      <div className="relative h-full min-h-[300px] bg-gray-100 rounded-lg overflow-hidden">
        <NoModelPlaceholder onBuildRequest={onBuildRequest} />
      </div>
    )
  }

  return (
    <div className="relative h-full min-h-[300px] bg-gray-900 rounded-lg overflow-hidden">
      <Canvas>
        <ModelScene meshData={meshData} />
      </Canvas>
      <SurfaceLegend surfaces={meshData.surfaces} />
    </div>
  )
}
