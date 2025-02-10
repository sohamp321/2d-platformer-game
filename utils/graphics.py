# import OpenGL.GL as gl
# import ctypes
# from OpenGL.GL.shaders import compileShader, compileProgram

# class Shader:
#     def __init__(self, vertex_src, fragment_src):
#         """
#         Compiles and links a shader program from the given vertex and fragment shader source strings.
#         """
#         self.ID = compileProgram(
#             compileShader(vertex_src, gl.GL_VERTEX_SHADER),
#             compileShader(fragment_src, gl.GL_FRAGMENT_SHADER)
#         )
    
#     def use(self):
#         """Activates this shader program."""
#         gl.glUseProgram(self.ID)
    
#     def delete(self):
#         """Deletes the shader program."""
#         gl.glDeleteProgram(self.ID)

# class VAO:
#     def __init__(self):
#         """Generates a new Vertex Array Object."""
#         self.ID = gl.glGenVertexArrays(1)
    
#     def bind(self):
#         """Binds this VAO."""
#         gl.glBindVertexArray(self.ID)
    
#     def unbind(self):
#         """Unbinds any VAO."""
#         gl.glBindVertexArray(0)
    
#     def link_attrib(self, vbo, layout, numComponents, type, stride, offset):
#         """
#         Links a vertex attribute from the given VBO to this VAO.
#         - layout: attribute location in the shader.
#         - numComponents: number of components per attribute.
#         - type: data type (e.g., gl.GL_FLOAT).
#         - stride: total byte size of one vertex.
#         - offset: byte offset to the attribute.
#         """
#         vbo.bind()
#         gl.glVertexAttribPointer(layout, numComponents, type, gl.GL_FALSE, stride, ctypes.c_void_p(offset))
#         gl.glEnableVertexAttribArray(layout)
#         vbo.unbind()
    
#     def delete(self):
#         """Deletes the VAO."""
#         gl.glDeleteVertexArrays(1, [self.ID])

# class VBO:
#     def __init__(self, data):
#         """
#         Creates a Vertex Buffer Object (VBO) and uploads the provided data (a numpy array).
#         """
#         self.ID = gl.glGenBuffers(1)
#         gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.ID)
#         gl.glBufferData(gl.GL_ARRAY_BUFFER, data.nbytes, data, gl.GL_STATIC_DRAW)
    
#     def bind(self):
#         """Binds this VBO."""
#         gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.ID)
    
#     def unbind(self):
#         """Unbinds the VBO."""
#         gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
    
#     def delete(self):
#         """Deletes the VBO."""
#         gl.glDeleteBuffers(1, [self.ID])

# class EBO:
#     def __init__(self, indices):
#         """
#         Creates an Element Buffer Object (EBO) and uploads the provided index data (a numpy array).
#         """
#         self.ID = gl.glGenBuffers(1)
#         gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ID)
#         gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW)
    
#     def bind(self):
#         """Binds this EBO."""
#         gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ID)
    
#     def unbind(self):
#         """Unbinds the EBO."""
#         gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)
    
#     def delete(self):
#         """Deletes the EBO."""
#         gl.glDeleteBuffers(1, [self.ID])


import OpenGL.GL as gl
import ctypes
from OpenGL.GL.shaders import compileShader, compileProgram

class Shader:
    def __init__(self, vertex_src, fragment_src):
        """
        Compiles and links a shader program from the given vertex and fragment shader source strings.
        """
        self.ID = compileProgram(
            compileShader(vertex_src, gl.GL_VERTEX_SHADER),
            compileShader(fragment_src, gl.GL_FRAGMENT_SHADER)
        )
    
    def use(self):
        gl.glUseProgram(self.ID)
    
    def delete(self):
        gl.glDeleteProgram(self.ID)

class VAO:
    def __init__(self):
        self.ID = gl.glGenVertexArrays(1)
    
    def bind(self):
        gl.glBindVertexArray(self.ID)
    
    def unbind(self):
        gl.glBindVertexArray(0)
    
    def link_attrib(self, vbo, layout, numComponents, type, stride, offset):
        vbo.bind()
        gl.glVertexAttribPointer(layout, numComponents, type, gl.GL_FALSE, stride, ctypes.c_void_p(offset))
        gl.glEnableVertexAttribArray(layout)
        vbo.unbind()
    
    def delete(self):
        gl.glDeleteVertexArrays(1, [self.ID])

class VBO:
    def __init__(self, data):
        self.ID = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.ID)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, data.nbytes, data, gl.GL_STATIC_DRAW)
    
    def bind(self):
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.ID)
    
    def unbind(self):
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
    
    def delete(self):
        gl.glDeleteBuffers(1, [self.ID])

class EBO:
    def __init__(self, indices):
        self.ID = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ID)
        gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW)
    
    def bind(self):
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ID)
    
    def unbind(self):
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)
    
    def delete(self):
        gl.glDeleteBuffers(1, [self.ID])
