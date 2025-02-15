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
